"""Hosted speech-to-text with Whisper on Groq. Used when SPEECH_PROVIDER=groq."""
import io
import json
import logging
import time
import urllib.error
import urllib.request
import uuid

from django.conf import settings

from .gemini import ProviderError
from .transcriber import NO_SPEECH_THRESHOLD, VERBATIM_PROMPT

logger = logging.getLogger(__name__)

URL = 'https://api.groq.com/openai/v1/audio/transcriptions'
EXTENSIONS = {'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'mp4', 'audio/wav': 'wav', 'audio/mpeg': 'mp3'}


def ready():
    if not settings.GROQ_API_KEY:
        return False, 'Add your Groq API key (GROQ_API_KEY) to the local .env file, then restart the app.'
    return True, ''


def _form(fields, audio, mime):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="answer.{EXTENSIONS.get(mime, "webm")}"\r\n'
                 f'Content-Type: {mime}\r\n\r\n'.encode() + audio + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def _once(audio, mime):
    body, content_type = _form({
        'model': settings.GROQ_STT_MODEL, 'language': 'en', 'temperature': '0',
        'response_format': 'verbose_json', 'prompt': VERBATIM_PROMPT,
    }, audio, mime)
    request = urllib.request.Request(URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {settings.GROQ_API_KEY}', 'Content-Type': content_type,
        'User-Agent': 'speako'})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read(1024 * 1024))
    except urllib.error.HTTPError as exc:
        logger.warning('Groq transcription failed: HTTP %s', exc.code)
        messages = {401: 'Groq rejected the API key. Check GROQ_API_KEY in .env, then restart the app.',
                    429: 'Groq rate limit reached. Wait a minute and record again.',
                    413: 'The recording is too large for Groq. Record a shorter answer.'}
        raise ProviderError(messages.get(exc.code, f'Groq returned HTTP {exc.code}. Record again shortly.'),
                            retryable=exc.code >= 500, http_status=exc.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning('Groq transcription failed: %s', type(exc).__name__)
        raise ProviderError('Groq connection failed or timed out. Nothing was evaluated. Record again.',
                            retryable=True) from None
    except ValueError:
        raise ProviderError('Groq returned an unreadable response. Record again.') from None
    segments = data.get('segments')
    if isinstance(segments, list):
        return ' '.join(str(s.get('text', '')).strip() for s in segments
                        if s.get('no_speech_prob', 0) < NO_SPEECH_THRESHOLD).strip()
    return str(data.get('text', '')).strip()


def has_speech(audio):
    """Check for speech on this server first. Whisper on Groq invents words ("Thank you.") for silence."""
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import get_speech_timestamps
    try:
        samples = decode_audio(io.BytesIO(audio), sampling_rate=16000)
    except Exception:
        raise ProviderError('The recording could not be processed. Record again. Nothing was evaluated.') from None
    return bool(get_speech_timestamps(samples))


def transcribe(audio, mime):
    """Return the spoken English as text. A server error or timeout gets one retry."""
    ok, message = ready()
    if not ok:
        raise ProviderError(message)
    if not has_speech(audio):
        return ''
    for attempt in range(2):
        try:
            return _once(audio, mime)
        except ProviderError as exc:
            if not exc.retryable or attempt == 1:
                raise
            time.sleep(0.5)
