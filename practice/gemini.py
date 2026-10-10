"""Only transcription and lesson conversation may call Gemini."""
import json
import re
import time
import urllib.error
import urllib.request
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from .models import ApiAttempt


class ProviderError(Exception):
    pass


def ready():
    if not settings.GEMINI_API_KEY:
        return False, 'Add your Gemini API key to the local .env file, then restart Django.'
    if not settings.GEMINI_FREE_TIER_CONFIRMED:
        return False, 'Check that your API project has no billing enabled, then set GEMINI_FREE_TIER_CONFIRMED=true in .env.'
    if settings.GEMINI_MODEL != 'gemini-2.5-flash-lite':
        return False, 'This version allows only gemini-2.5-flash-lite. Review pricing before changing models.'
    return True, ''


def usage():
    rows = ApiAttempt.objects.all()
    totals = rows.aggregate(guard=Sum('guard_usd'), inputs=Sum('prompt_tokens'), outputs=Sum('output_tokens'))
    return {'attempts': rows.count(), 'guard_usd': round(totals['guard'] or 0, 4),
            'external_spend_usd': settings.RECORDED_EXTERNAL_SPEND_USD,
            'budget_usd': min(settings.PROJECT_BUDGET_USD, 10),
            'prompt_tokens': totals['inputs'] or 0, 'output_tokens': totals['outputs'] or 0,
            'billing_note': 'Free-tier assumption. Local guard is not an invoice; verify actual usage in AI Studio.'}


def generate(purpose, parts, system, schema):
    if purpose not in {'transcription', 'conversation'}:
        raise ProviderError('This API purpose is not allowed.')
    ok, message = ready()
    if not ok:
        raise ProviderError(message)
    # Writing first obtains SQLite's writer lock, making reservation checks serial.
    with transaction.atomic():
        attempt = ApiAttempt.objects.create(purpose=purpose)
        ledger = usage()
        if (ledger['guard_usd'] + ledger['external_spend_usd'] > ledger['budget_usd']
                or ledger['attempts'] > settings.MAX_API_ATTEMPTS):
            raise ProviderError('Project usage guard reached. Stop and review the $10 project budget before making more requests.')
    payload = {
        'systemInstruction': {'parts': [{'text': system}]},
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 512,
                             'responseMimeType': 'application/json', 'responseSchema': schema},
    }
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent'
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        'Content-Type': 'application/json', 'x-goog-api-key': settings.GEMINI_API_KEY}, method='POST')
    begun = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read(1024 * 1024))
        metadata = data.get('usageMetadata', {})
        attempt.prompt_tokens = max(0, int(metadata.get('promptTokenCount', 0)))
        attempt.output_tokens = max(0, int(metadata.get('candidatesTokenCount', 0))) + max(0, int(metadata.get('thoughtsTokenCount', 0)))
        # Audio-rate pricing for ALL input tokens is deliberately conservative.
        attempt.guard_usd = max(0.02, (attempt.prompt_tokens * 0.30 + attempt.output_tokens * 0.40) / 1_000_000)
        content = ''.join(p.get('text', '') for p in data.get('candidates', [{}])[0].get('content', {}).get('parts', []))
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError('Expected object')
        attempt.status = 'success'
        return result
    except urllib.error.HTTPError as exc:
        attempt.status = f'http_{exc.code}'
        messages = {429: 'Gemini quota or rate limit reached. Wait and retry; no paid fallback is used.',
                    400: 'Gemini rejected the request. Check the model and audio format.',
                    403: 'Gemini access denied. Check the key, API project and regional access.',
                    404: 'The configured Gemini model is unavailable for this project.'}
        raise ProviderError(messages.get(exc.code, 'Gemini is temporarily unavailable. Retry this step.')) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        attempt.status = 'network_error'
        raise ProviderError('Gemini connection failed or timed out. Check your connection and retry.') from None
    except (ValueError, KeyError, IndexError, TypeError):
        attempt.status = 'invalid_output'
        raise ProviderError('Gemini returned an unreadable response. This turn was not advanced. Retry this step.') from None
    finally:
        attempt.elapsed_ms = (time.perf_counter() - begun) * 1000
        attempt.save()
