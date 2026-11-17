"""Local speech-to-text (faster-whisper). A fake model is used, so no model is downloaded."""
import json
import re
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from . import providers, transcriber
from .models import ApiUsage, LessonAttempt, Lesson, LessonWord, Turn, User


class Segment:
    def __init__(self, text, no_speech_prob=0.01):
        self.text = text
        self.no_speech_prob = no_speech_prob


class FakeModel:
    def __init__(self, segments=(), error=None):
        self.segments = list(segments)
        self.error = error
        self.calls = []

    def transcribe(self, audio, **options):
        self.calls.append(options)
        if self.error:
            raise self.error
        return iter(self.segments), None


@override_settings(SPEECH_PROVIDER='whisper')
class LocalSpeechTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='test-pass')
        self.client.force_login(self.user)
        lesson = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.attempt = LessonAttempt.objects.create(learner=self.user, lesson=lesson, opening_line='Hello!')

    def upload(self):
        return self.client.post('/api/transcribe/', {
            'attempt_id': str(self.attempt.pk),
            'audio': SimpleUploadedFile('answer.webm', b'webm-bytes', content_type='audio/webm')})

    def assert_turn_unchanged(self):
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.busy)
        self.assertFalse(self.attempt.pending_id)
        self.assertFalse(Turn.objects.exists())

    @patch('practice.gemini.generate')
    def test_local_model_transcribes_verbatim_without_api_call(self, gemini_call):
        model = FakeModel([Segment(' I would likes tea, '), Segment('please. ')])
        with patch('practice.transcriber._load', return_value=model):
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt']['pending']['text'], 'I would likes tea, please.')
        gemini_call.assert_not_called()
        self.assertEqual(ApiUsage.objects.count(), 0)

    def test_whisper_settings_keep_mistakes_and_filter_silence(self):
        model = FakeModel([Segment('Can I has the bill?')])
        with patch('practice.transcriber._load', return_value=model):
            self.upload()
        options = model.calls[0]
        self.assertEqual(options['language'], 'en')
        self.assertTrue(options['vad_filter'])
        self.assertEqual(options['temperature'], 0.0)
        self.assertFalse(options['condition_on_previous_text'])
        self.assertEqual(options['initial_prompt'], transcriber.VERBATIM_PROMPT)

    def test_silence_and_noise_return_no_speech(self):
        model = FakeModel([Segment('Thank you.', no_speech_prob=0.9)])
        with patch('practice.transcriber._load', return_value=model):
            response = self.upload()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'NO_SPEECH')
        self.assert_turn_unchanged()

    def test_missing_model_fails_safely(self):
        with patch('practice.transcriber._load', side_effect=OSError('model files not found')):
            response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['error']['code'], 'TRANSCRIPTION_FAILED')
        self.assertIn('WHISPER_MODEL', response.json()['error']['message'])
        self.assert_turn_unchanged()

    def test_unreadable_recording_fails_safely(self):
        model = FakeModel(error=ValueError('invalid data found when processing input'))
        with patch('practice.transcriber._load', return_value=model):
            response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('Record again', response.json()['error']['message'])
        self.assert_turn_unchanged()

    def test_verbatim_prompt_has_no_lesson_words(self):
        prompt_words = set(re.findall(r"[a-z']+", transcriber.VERBATIM_PROMPT.lower()))
        lesson_words = set(LessonWord.objects.values_list('word', flat=True))
        self.assertTrue(lesson_words)
        self.assertEqual(prompt_words & lesson_words, set())

    @override_settings(SPEECH_PROVIDER='gemini')
    @patch('practice.transcriber._load')
    @patch('practice.gemini.generate', return_value={'transcript': 'water please'})
    def test_gemini_setting_keeps_api_path(self, gemini_call, local_model):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(gemini_call.call_args.args[0], 'transcription')
        local_model.assert_not_called()

    @override_settings(SPEECH_PROVIDER='cloud')
    @patch('practice.transcriber._load')
    @patch('practice.gemini.generate')
    def test_unknown_provider_is_refused_without_any_call(self, gemini_call, local_model):
        response = self.upload()
        self.assertEqual(response.status_code, 502)
        self.assertIn('SPEECH_PROVIDER', response.json()['error']['message'])
        gemini_call.assert_not_called()
        local_model.assert_not_called()
        self.assert_turn_unchanged()

    @patch('practice.transcriber.preload')
    def test_model_preloads_only_for_local_speech(self, preload):
        providers.preload_speech_model()
        preload.assert_called_once()
        with override_settings(SPEECH_PROVIDER='gemini'):
            providers.preload_speech_model()
        preload.assert_called_once()
