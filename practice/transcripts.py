import time
import uuid

from django.http import JsonResponse
from . import providers
from .models import LessonAttempt

MIMES = {'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/wav', 'audio/mpeg'}


def fail(status, code, message):
    return JsonResponse({'error': {'code': code, 'message': message}}, status=status)


def process(request, attempt, snapshot):
    audio = request.FILES.get('audio')
    if not audio or not audio.size:
        return fail(400, 'AUDIO_REQUIRED', 'Record an answer first.')
    if audio.size > 4 * 1024 * 1024:
        return fail(413, 'AUDIO_TOO_LARGE', 'Use a recording under 4 MB.')
    mime = (audio.content_type or '').split(';')[0].strip().lower()
    if mime not in MIMES:
        return fail(415, 'UNSUPPORTED_AUDIO', 'This audio format is unsupported.')
    return locked(request, attempt, snapshot, audio.read(), mime)


def locked(request, attempt, snapshot, audio=None, mime=None, pending_id=None):
    if attempt.status != 'In progress':
        return fail(409, 'CLOSED', 'This lesson attempt has ended.')
    if not LessonAttempt.objects.filter(pk=attempt.pk, status='In progress', busy=False).update(busy=True):
        return fail(409, 'BUSY', 'Another step is still running. Wait before trying again.')
    begun = time.perf_counter()
    try:
        attempt.refresh_from_db()
        if audio is None:
            if not isinstance(pending_id, str) or not pending_id or pending_id != attempt.pending_id:
                return fail(409, 'STALE', 'This transcript is no longer waiting for confirmation.')
            attempt.pending_transcript = ''
            attempt.pending_id = ''
        else:
            if attempt.pending_id:
                return fail(409, 'PENDING', 'Confirm or discard the existing transcript first.')
            try:
                result = providers.transcribe(audio, mime)
            except providers.ProviderError as exc:
                return fail(502, 'TRANSCRIPTION_FAILED', str(exc))
            transcript = result.get('transcript') if isinstance(result, dict) else None
            if not isinstance(transcript, str) or len(transcript) > 1000:
                return fail(502, 'INVALID_TRANSCRIPT', 'The recognition result was invalid. Record again.')
            if not transcript.strip():
                return fail(422, 'NO_SPEECH', 'No clear speech was detected. Nothing was evaluated. Record again.')
            attempt.pending_transcript = transcript.strip()
            attempt.pending_id = str(uuid.uuid4())
        attempt.save(update_fields=['pending_transcript', 'pending_id'])
        return JsonResponse({'attempt': snapshot(attempt), 'server_ms': (time.perf_counter() - begun) * 1000})
    finally:
        LessonAttempt.objects.filter(pk=attempt.pk).update(busy=False)
