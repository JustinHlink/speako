"""Conversation replies from Claude Haiku. Every call passes the same $10 usage guard as before."""
import json
import logging

import anthropic
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .gemini import ProviderError, usage
from .models import ApiUsage

logger = logging.getLogger(__name__)

ALLOWED_MODEL = 'claude-haiku-5-5'
# Claude Haiku 5.5 price per 1M tokens, used only for the local estimate (not an invoice).
INPUT_USD, OUTPUT_USD = 0.10, 0.50
RESERVED_USD = 0.02


def ready():
    if not settings.ANTHROPIC_API_KEY:
        return False, 'Add your Claude API key (ANTHROPIC_API_KEY) to the local .env file, then restart the app.'
    if settings.CLAUDE_MODEL != ALLOWED_MODEL:
        return False, f'This version allows only {ALLOWED_MODEL}. Review pricing before changing models.'
    return True, ''


def json_schema(schema):
    """Turn the shared reply schema (OBJECT, STRING ...) into standard JSON Schema."""
    result = {'type': schema['type'].lower()}
    if 'properties' in schema:
        result['properties'] = {name: json_schema(value) for name, value in schema['properties'].items()}
        result['required'] = list(schema.get('required', []))
        result['additionalProperties'] = False
    return result


def generate(parts, system, schema):
    ok, message = ready()
    if not ok:
        raise ProviderError(message)
    # Writing first obtains SQLite's writer lock, making reservation checks serial.
    with transaction.atomic():
        attempt = ApiUsage.objects.create(environment_id='local', call_type='Reply', reserved_usd=RESERVED_USD)
        ledger = usage()
        if (ledger['guard_usd'] + ledger['external_spend_usd'] > ledger['budget_usd']
                or ledger['attempts'] > settings.MAX_API_ATTEMPTS):
            raise ProviderError('Project usage guard reached. Stop and review the $10 project budget before making more requests.')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=25.0, max_retries=0)
    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=system,
            messages=[{'role': 'user', 'content': '\n'.join(part['text'] for part in parts)}],
            thinking={'type': 'disabled'},
            output_config={'effort': 'low', 'format': {'type': 'json_schema', 'schema': json_schema(schema)}},
        )
        attempt.input_tokens = max(0, response.usage.input_tokens or 0)
        attempt.output_tokens = max(0, response.usage.output_tokens or 0)
        attempt.estimated_usd = (attempt.input_tokens * INPUT_USD + attempt.output_tokens * OUTPUT_USD) / 1_000_000
        if response.stop_reason == 'refusal':
            attempt.status = 'Failed'
            raise ProviderError('Claude declined to answer this turn. Your answer is saved. Try Continue again.')
        if response.stop_reason == 'max_tokens':
            attempt.status = 'Failed'
            raise ProviderError('Claude returned an incomplete reply. This turn was not advanced. Retry this step.')
        text = next(block.text for block in response.content if block.type == 'text')
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError('Expected object')
        attempt.status = 'Success'
        result['_api_attempt_id'] = attempt.pk
        return result
    except anthropic.AuthenticationError:
        attempt.status = 'Unknown'
        raise ProviderError('Claude rejected the API key. Check ANTHROPIC_API_KEY in .env, then restart the app.') from None
    except anthropic.PermissionDeniedError:
        attempt.status = 'Unknown'
        raise ProviderError('Claude access denied for this key. Check the key and its workspace.') from None
    except anthropic.NotFoundError:
        attempt.status = 'Unknown'
        raise ProviderError('The configured Claude model is unavailable for this key.') from None
    except anthropic.RateLimitError:
        attempt.status = 'Unknown'
        raise ProviderError('Claude rate limit reached. Wait and retry; no paid fallback is used.', retryable=True, http_status=429) from None
    except anthropic.APIStatusError as exc:
        attempt.status = 'Unknown'
        logger.warning('Claude reply failed: HTTP %s; usage reservation retained', exc.status_code)
        raise ProviderError(f'Claude returned HTTP {exc.status_code}. Retry this step shortly.',
                            retryable=exc.status_code >= 500, http_status=exc.status_code) from None
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        attempt.status = 'Unknown'
        logger.warning('Claude reply failed: %s; usage reservation retained', type(exc).__name__)
        raise ProviderError('Claude connection failed or timed out. Your turn was not advanced. Retry shortly.', retryable=True) from None
    except (StopIteration, ValueError, KeyError, TypeError):
        attempt.status = 'Failed'
        raise ProviderError('Claude returned an unreadable response. This turn was not advanced. Retry this step.') from None
    finally:
        attempt.finished_at = timezone.now()
        attempt.save()
