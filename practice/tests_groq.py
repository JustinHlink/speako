"""Hosted speech-to-text on Groq. These tests fake the network, so they never reach Groq."""
import io
import json
import urllib.error
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from . import providers
from .groq_stt import has_speech as real_has_speech
from .models import Lesson, LessonAttempt, Turn, User
from .transcriber import VERBATIM_PROMPT

GROQ_READY = dict(SPEECH_PROVIDER='groq', SPEECH_FALLBACK='none', GROQ_API_KEY='test-only',
                  GROQ_STT_MODEL='whisper-large-v3',
                  REPLY_PROVIDER='claude', ANTHROPIC_API_KEY='test-only', CLAUDE_MODEL='claude-haiku-5-5')


def groq_reply(*segments):
    body = {'text': ' '.join(t for t, _ in segments),
            'segments': [{'text': t, 'no_speech_prob': p} for t, p in segments]}
    return io.BytesIO(json.dumps(body).encode())


def http_error(code):
    return urllib.error.HTTPError('https://api.groq.com', code, 'error', {}, None)


@override_settings(**GROQ_READY)
class GroqSpeechTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='test-pass')
        self.client.force_login(self.user)
        lesson = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.attempt = LessonAttempt.objects.create(learner=self.user, lesson=lesson, opening_line='Hello!')
        gate = patch('practice.groq_stt.has_speech', return_value=True)  # The fake bytes are not real audio.
        self.has_speech = gate.start()
        self.addCleanup(gate.stop)

    def upload(self):
        return self.client.post('/api/transcribe/', {
            'attempt_id': str(self.attempt.pk),
            'audio': SimpleUploadedFile('answer.webm', b'webm-bytes', content_type='audio/webm')})

    def assert_turn_unchanged(self):
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.busy)
        self.assertFalse(self.attempt.pending_id)
        self.assertFalse(Turn.objects.exists())

    @patch('practice.transcriber._load')
    @patch('urllib.request.urlopen')
    def test_groq_transcribes_verbatim_with_the_same_prompt(self, network, local_model):
        network.return_value = groq_reply((' I would likes tea, ', 0.01), ('please.', 0.02))
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt']['pending']['text'], 'I would likes tea, please.')
        request = network.call_args.args[0]
        body = request.data.decode('latin-1')
        self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/audio/transcriptions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-only')
        for field in ('whisper-large-v3', 'verbose_json', VERBATIM_PROMPT, 'name="language"\r\n\r\nen'):
            self.assertIn(field, body)
        self.assertIn('filename="answer.webm"', body)
        local_model.assert_not_called()

    @patch('urllib.request.urlopen')
    def test_silence_segments_are_dropped(self, network):
        network.return_value = groq_reply(('Thank you.', 0.95))
        response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'NO_SPEECH')
        self.assert_turn_unchanged()

    @patch('urllib.request.urlopen')
    def test_no_speech_skips_groq(self, network):
        self.has_speech.return_value = False
        response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'NO_SPEECH')
        network.assert_not_called()
        self.assert_turn_unchanged()

    @patch('urllib.request.urlopen')
    def test_unreadable_recording_is_not_sent(self, network):
        self.has_speech.side_effect = real_has_speech  # Run the real check on bytes that are not audio.
        response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('Record again', response.json()['error']['message'])
        network.assert_not_called()
        self.assert_turn_unchanged()

    @patch('practice.groq_stt.time.sleep')
    @patch('urllib.request.urlopen')
    def test_server_error_is_retried_once(self, network, sleep):
        network.side_effect = [http_error(503), groq_reply(('Me want the soup.', 0.01))]
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(network.call_count, 2)

    @patch('practice.groq_stt.time.sleep')
    @patch('urllib.request.urlopen', side_effect=TimeoutError)
    def test_timeout_has_only_two_attempts(self, network, sleep):
        response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('timed out', response.json()['error']['message'])
        self.assertEqual(network.call_count, 2)
        self.assert_turn_unchanged()

    @patch('urllib.request.urlopen', side_effect=http_error(401))
    def test_bad_key_is_not_retried(self, network):
        response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('GROQ_API_KEY', response.json()['error']['message'])
        self.assertEqual(network.call_count, 1)
        self.assert_turn_unchanged()

    @patch('urllib.request.urlopen', side_effect=http_error(429))
    def test_rate_limit_gives_a_clear_message(self, network):
        response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('rate limit', response.json()['error']['message'])

    @override_settings(GROQ_API_KEY='')
    @patch('urllib.request.urlopen')
    def test_missing_key_explains_the_setup(self, network):
        status = self.client.get('/api/status/').json()
        self.assertFalse(status['api_ready'])
        self.assertIn('GROQ_API_KEY', status['setup_message'])
        self.assertEqual(self.upload().status_code, 502)
        network.assert_not_called()

    @override_settings(SPEECH_FALLBACK='whisper')
    @patch('practice.groq_stt.time.sleep')
    @patch('urllib.request.urlopen', side_effect=TimeoutError)
    def test_groq_failure_falls_back_to_the_local_model(self, network, sleep):
        class LocalModel:
            def transcribe(self, audio, **options):
                return iter([type('Segment', (), {'text': 'Can I has the bill?', 'no_speech_prob': 0.01})()]), None
        with patch('practice.transcriber._load', return_value=LocalModel()):
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt']['pending']['text'], 'Can I has the bill?')
        self.assertEqual(network.call_count, 2)

    @patch('practice.transcriber.preload')
    def test_local_model_preloads_only_when_it_is_the_backup(self, preload):
        providers.preload_speech_model()
        preload.assert_not_called()
        with override_settings(SPEECH_FALLBACK='whisper'):
            providers.preload_speech_model()
        preload.assert_called_once()
