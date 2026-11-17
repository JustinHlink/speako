"""Local speech-to-text with faster-whisper. The audio stays on this computer and uses no API budget."""
import io
import logging
import threading

from django.conf import settings

from .gemini import ProviderError

logger = logging.getLogger(__name__)

# Whisper reads this as earlier speech, so it keeps beginner mistakes instead of repairing them.
# It has no lesson words, so it cannot add a target word to a learner's transcript.
VERBATIM_PROMPT = "Um, he go to school yesterday. She don't likes it. They is happy."
# Whisper rates each segment; segments that are probably silence or noise are dropped.
NO_SPEECH_THRESHOLD = 0.6

_model = None
_load_lock = threading.Lock()
_run_lock = threading.Lock()


def _load():
    global _model
    with _load_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(settings.WHISPER_MODEL, device='cpu', compute_type=settings.WHISPER_COMPUTE_TYPE)
    return _model


def preload():
    """Load the model in the background when the server starts, so the first answer is not slow."""
    def run():
        try:
            _load()
            logger.info('Speech model %s is ready.', settings.WHISPER_MODEL)
        except Exception as exc:  # The first transcription request reports the error to the learner.
            logger.warning('Speech model %s did not load: %s', settings.WHISPER_MODEL, type(exc).__name__)
    threading.Thread(target=run, name='speech-model-preload', daemon=True).start()


def transcribe(audio):
    """Return the spoken English as text. Return '' for silence or noise."""
    try:
        model = _load()
    except Exception as exc:
        logger.warning('Speech model %s did not load: %s', settings.WHISPER_MODEL, type(exc).__name__)
        raise ProviderError('The speech model could not be loaded. Check WHISPER_MODEL in .env, then restart the app.') from None
    try:
        # One transcription at a time keeps a laptop CPU responsive.
        with _run_lock:
            segments, _ = model.transcribe(
                io.BytesIO(audio), language='en', beam_size=5, temperature=0.0,
                condition_on_previous_text=False, initial_prompt=VERBATIM_PROMPT, vad_filter=True)
            return ' '.join(s.text.strip() for s in segments if s.no_speech_prob < NO_SPEECH_THRESHOLD).strip()
    except Exception as exc:
        logger.warning('Local transcription failed: %s', type(exc).__name__)
        raise ProviderError('The recording could not be processed. Record again. Nothing was evaluated.') from None
