"""Claude Haiku replies. These tests fake the SDK client, so they make no network calls and use no budget."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import anthropic
from django.conf import settings
from django.test import TestCase, override_settings
from . import claude
from .models import ApiUsage, Lesson, LessonAttempt, Turn, User

GOOD = {'reply': 'Would you like water or tea?', 'correction_explanation': '',
        'corrected_example': '', 'off_topic': False}
OFF_LIST = {'reply': 'Would you like quantum physics?', 'correction_explanation': '',
            'corrected_example': '', 'off_topic': False}
CLAUDE_READY = dict(REPLY_PROVIDER='claude', SPEECH_PROVIDER='whisper', ANTHROPIC_API_KEY='test-only',
                    CLAUDE_MODEL='claude-haiku-5-5', PROJECT_BUDGET_USD=10, RECORDED_EXTERNAL_SPEND_USD=0,
                    MAX_API_ATTEMPTS=500)


def message(result, stop_reason='end_turn'):
    return SimpleNamespace(stop_reason=stop_reason, usage=SimpleNamespace(input_tokens=900, output_tokens=60),
                           content=[SimpleNamespace(type='text', text=json.dumps(result))])


def api_error(cls):
    return cls.__new__(cls)  # The handler only checks the error class.


@override_settings(**CLAUDE_READY)
class ClaudeReplyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='test-pass')
        self.client.force_login(self.user)
        lesson = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.attempt = LessonAttempt.objects.create(learner=self.user, lesson=lesson, opening_line='Hello!',
                                                   pending_transcript='I would likes tea.', pending_id='pending-1')
        patcher = patch('practice.claude.anthropic.Anthropic')
        self.sdk = patcher.start()
        self.addCleanup(patcher.stop)
        self.create = self.sdk.return_value.messages.create

    def continue_turn(self):
        return self.client.post('/api/reply/', json.dumps(
            {'attempt_id': str(self.attempt.pk), 'pending_id': 'pending-1'}), content_type='application/json')

    def assert_turn_unchanged(self):
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_id, 'pending-1')
        self.assertFalse(self.attempt.busy)
        self.assertFalse(Turn.objects.exists())

    def test_reply_is_saved_and_logged_in_the_usage_guard(self):
        self.create.return_value = message(GOOD)
        response = self.continue_turn()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Turn.objects.get().ai_reply, 'Would you like water or tea?')
        row = ApiUsage.objects.get()
        self.assertEqual((row.call_type, row.status, row.input_tokens, row.output_tokens), ('Reply', 'Success', 900, 60))
        self.assertAlmostEqual(row.estimated_usd, (900 * 0.10 + 60 * 0.50) / 1_000_000)
        self.assertEqual(row.reserved_usd, 0.02)

    def test_request_uses_haiku_json_schema_and_no_automatic_retry(self):
        self.create.return_value = message(GOOD)
        self.continue_turn()
        self.assertEqual(self.sdk.call_args.kwargs['max_retries'], 0)
        request = self.create.call_args.kwargs
        self.assertEqual(request['model'], 'claude-haiku-5-5')
        self.assertEqual(request['thinking'], {'type': 'disabled'})
        schema = request['output_config']['format']['schema']
        self.assertEqual(request['output_config']['format']['type'], 'json_schema')
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), set(GOOD))
        self.assertEqual(schema['properties']['off_topic'], {'type': 'boolean'})
        self.assertIn('I would likes tea.', request['messages'][0]['content'])

    def test_off_list_reply_is_rewritten_once_then_rejected(self):
        self.create.return_value = message(OFF_LIST)
        response = self.continue_turn()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.create.call_count, 2)
        self.assertEqual(list(ApiUsage.objects.values_list('status', flat=True)), ['Validation rejected'] * 2)
        self.assert_turn_unchanged()

    def test_refusal_keeps_the_transcript(self):
        self.create.return_value = message({}, stop_reason='refusal')
        response = self.continue_turn()
        self.assertEqual(response.status_code, 502)
        self.assertIn('declined', response.json()['error']['message'])
        self.assert_turn_unchanged()

    def test_bad_key_gives_a_clear_message(self):
        self.create.side_effect = api_error(anthropic.AuthenticationError)
        response = self.continue_turn()
        self.assertEqual(response.status_code, 502)
        self.assertIn('ANTHROPIC_API_KEY', response.json()['error']['message'])
        self.assertEqual(ApiUsage.objects.get().status, 'Unknown')
        self.assert_turn_unchanged()

    def test_connection_failure_keeps_reservation_and_transcript(self):
        self.create.side_effect = api_error(anthropic.APIConnectionError)
        response = self.continue_turn()
        self.assertEqual(response.status_code, 502)
        self.assertIn('timed out', response.json()['error']['message'])
        self.assertEqual(ApiUsage.objects.get().status, 'Unknown')
        self.assert_turn_unchanged()

    def test_unreadable_output_is_not_saved(self):
        self.create.return_value = SimpleNamespace(stop_reason='end_turn', usage=SimpleNamespace(
            input_tokens=1, output_tokens=1), content=[SimpleNamespace(type='text', text='not json')])
        self.assertEqual(self.continue_turn().status_code, 502)
        self.assertEqual(ApiUsage.objects.get().status, 'Failed')
        self.assert_turn_unchanged()

    @override_settings(PROJECT_BUDGET_USD=0.01)
    def test_budget_guard_stops_before_any_call(self):
        response = self.continue_turn()
        self.assertEqual(response.status_code, 502)
        self.assertIn('usage guard', response.json()['error']['message'])
        self.create.assert_not_called()
        self.assertFalse(ApiUsage.objects.exists())
        self.assert_turn_unchanged()

    @override_settings(REPLY_PROVIDER='gemini')
    @patch('practice.gemini.generate', return_value=GOOD)
    def test_gemini_setting_keeps_the_old_reply_path(self, gemini_call):
        self.assertEqual(self.continue_turn().status_code, 200)
        self.assertEqual(gemini_call.call_args.args[0], 'conversation')
        self.create.assert_not_called()


@override_settings(**CLAUDE_READY)
class ClaudeReadinessTests(TestCase):
    def status(self):
        return self.client.get('/api/status/').json()

    def test_ready_with_key_and_allowed_model(self):
        self.assertTrue(self.status()['api_ready'])

    @override_settings(ANTHROPIC_API_KEY='')
    def test_missing_key_explains_the_setup(self):
        data = self.status()
        self.assertFalse(data['api_ready'])
        self.assertIn('ANTHROPIC_API_KEY', data['setup_message'])

    @override_settings(CLAUDE_MODEL='claude-opus-5-5')
    def test_only_the_budgeted_model_is_allowed(self):
        self.assertFalse(self.status()['api_ready'])

    @override_settings(REPLY_PROVIDER='other')
    def test_unknown_reply_provider_is_not_ready(self):
        self.assertIn('REPLY_PROVIDER', self.status()['setup_message'])

    def test_json_schema_conversion(self):
        self.assertEqual(claude.json_schema({'type': 'OBJECT', 'properties': {'a': {'type': 'STRING'}}, 'required': ['a']}),
                         {'type': 'object', 'properties': {'a': {'type': 'string'}}, 'required': ['a'],
                          'additionalProperties': False})


class TestSafetyNetTests(TestCase):
    def test_suite_runs_without_real_api_keys(self):
        self.assertEqual(settings.ANTHROPIC_API_KEY, '')
        self.assertEqual(settings.GEMINI_API_KEY, '')
