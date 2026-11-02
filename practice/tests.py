import io
import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import *
from .lesson import LESSON, make_summary
from .gemini import generate, ProviderError


GOOD = {'reply': 'Would you like water?', 'correction_explanation': '', 'corrected_example': '', 'off_topic': False}


class WorkflowTests(TestCase):
    def setUp(self):
        self.client.post('/api/start/')
        self.session = PracticeSession.objects.get()

    def pending(self, text='I would like chicken please'):
        self.session.pending = text
        self.session.save()

    def reply(self, count=0):
        return self.client.post('/api/reply/', json.dumps({'expected_turn': count}), content_type='application/json')

    def test_discard_never_calls_ai_or_enters_summary(self):
        self.pending('misheard speech')
        with patch('practice.gemini.generate') as provider:
            self.client.post('/api/discard/')
            self.assertEqual(self.reply().status_code, 409)
            provider.assert_not_called()
        self.session.refresh_from_db()
        self.assertEqual(self.session.turns, [])
        self.assertEqual(self.session.pending, '')

    @patch('practice.gemini.generate', return_value={'transcript': ''})
    def test_silence_is_not_submitted_for_evaluation(self, provider):
        response = self.client.post('/api/transcribe/', {'audio': SimpleUploadedFile('a.webm', b'fake', content_type='audio/webm')})
        self.assertEqual(response.status_code, 422)
        self.session.refresh_from_db()
        self.assertEqual(self.session.pending, '')
        self.assertEqual(provider.call_args.args[0], 'transcription')

    @patch('practice.gemini.generate', side_effect=ProviderError('quota reached'))
    def test_failure_preserves_pending_text_and_turn(self, provider):
        self.pending()
        self.assertEqual(self.reply().status_code, 502)
        self.session.refresh_from_db()
        self.assertTrue(self.session.pending)
        self.assertEqual(self.session.turns, [])
        self.assertFalse(self.session.busy)

    @patch('practice.gemini.generate', return_value=GOOD)
    def test_success_and_duplicate_do_not_advance_twice(self, provider):
        self.pending()
        self.assertEqual(self.reply().status_code, 200)
        self.assertEqual(self.reply().status_code, 409)
        self.session.refresh_from_db()
        self.assertEqual(len(self.session.turns), 1)
        self.assertEqual(provider.call_count, 1)

    @patch('practice.gemini.generate', return_value=GOOD)
    def test_fifth_turn_persists_complete_summary_without_summary_api(self, provider):
        for count in range(5):
            self.session.refresh_from_db()
            self.pending()
            response = self.reply(count)
            self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'completed')
        self.assertIn('chicken', self.session.summary['used'])
        self.assertIn('bill', self.session.summary['unused'])
        self.assertEqual(self.session.summary['corrections'], [])
        self.assertEqual(provider.call_count, 5)
        self.assertTrue(all(call.args[0] == 'conversation' for call in provider.call_args_list))
        self.assertEqual(self.client.get('/api/status/').json()['session']['status'], 'completed')

    def test_early_exit_has_no_summary(self):
        self.pending()
        self.client.post('/api/exit/')
        self.session.refresh_from_db()
        self.assertEqual(self.session.summary, {})
        self.assertEqual(self.session.pending, '')
        self.assertEqual(self.session.status, 'exited')

    @patch('practice.gemini.generate', return_value={**GOOD, 'off_topic': True, 'correction_explanation': 'Wrong.', 'corrected_example': 'I would like water.'})
    def test_off_topic_is_not_allowed_to_be_labeled_incorrect(self, provider):
        self.pending('I like football')
        self.assertEqual(self.reply().status_code, 502)
        self.session.refresh_from_db()
        self.assertEqual(self.session.turns, [])

    @patch('practice.gemini.generate', return_value={**GOOD, 'reply': 'Would you like quantum physics?'})
    def test_outside_vocabulary_is_rejected_without_auto_api_retry(self, provider):
        self.pending()
        self.assertEqual(self.reply().status_code, 502)
        self.assertEqual(provider.call_count, 1)

    @patch('practice.gemini.generate', return_value={**GOOD, 'reply': 'No problem. Try chicken with rice or soup.'})
    def test_unsure_learner_receives_guidance_without_a_correction(self, provider):
        self.pending("I don't know, I don't know.")
        response = self.reply()
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.pending, '')
        self.assertEqual(len(self.session.turns), 1)
        self.assertIsNone(self.session.turns[0]['correction'])
        self.assertEqual(self.session.turns[0]['reply'], 'No problem. Try chicken with rice or soup.')
        self.assertEqual(provider.call_count, 1)

    @patch('practice.gemini.generate', return_value={**GOOD, 'reply': 'No problem. Would you like chicken or soup?', 'off_topic': True})
    def test_off_topic_answer_can_receive_gentle_redirection(self, provider):
        self.pending('I like football.')
        self.assertEqual(self.reply().status_code, 200)
        self.session.refresh_from_db()
        self.assertTrue(self.session.turns[0]['off_topic'])
        self.assertIsNone(self.session.turns[0]['correction'])

    def test_another_browser_cannot_see_session(self):
        self.assertIsNone(Client().get('/api/status/').json()['session'])

    def test_csrf_required_for_mutation(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/api/start/').status_code, 403)

    def test_unconfigured_lesson_cannot_start(self):
        with patch.dict(LESSON, {'target_words': []}):
            self.assertEqual(self.client.post('/api/start/').status_code, 400)

    def test_existing_busy_session_rejects_parallel_reply(self):
        self.pending()
        self.session.busy = True
        self.session.save()
        with patch('practice.gemini.generate') as provider:
            self.assertEqual(self.reply().status_code, 409)
            provider.assert_not_called()


@override_settings(GEMINI_API_KEY='test-only-not-a-real-key', GEMINI_FREE_TIER_CONFIRMED=True, GEMINI_MODEL='gemini-3.1-flash-lite', PROJECT_BUDGET_USD=10, RECORDED_EXTERNAL_SPEND_USD=0)
class BudgetTests(TestCase):
    def test_only_two_api_purposes_allowed(self):
        with self.assertRaises(ProviderError):
            generate('summary', [], '', {})
        self.assertEqual(ApiUsage.objects.count(), 0)

    @override_settings(PROJECT_BUDGET_USD=0.01)
    @patch('urllib.request.urlopen')
    def test_budget_guard_blocks_before_network(self, network):
        with self.assertRaises(ProviderError):
            generate('conversation', [], '', {})
        network.assert_not_called()
        self.assertEqual(ApiUsage.objects.count(), 0)

    @patch('urllib.request.urlopen', side_effect=TimeoutError)
    def test_failed_request_remains_in_project_ledger(self, network):
        with self.assertRaises(ProviderError):
            generate('transcription', [], '', {})
        attempt = ApiUsage.objects.get()
        self.assertEqual(attempt.status, 'network_error')
        self.assertEqual(attempt.guard_usd, 0.02)

    @override_settings(GEMINI_FREE_TIER_CONFIRMED=False)
    @patch('urllib.request.urlopen')
    def test_no_api_until_free_project_confirmed(self, network):
        with self.assertRaises(ProviderError):
            generate('conversation', [], '', {})
        network.assert_not_called()

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'secure_password123'
        self.learner = User.objects.create_user(
            username='test_learner',
            password=self.password,
            role='Learner'
        )

    def test_login_success(self):
        response = self.client.post(
            '/api/auth/login/',
            json.dumps({'username': 'test_learner', 'password': self.password}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'test_learner')
        self.assertEqual(data['user']['role'], 'Learner')

    def test_login_invalid_credentials_returns_401(self):
        response = self.client.post(
            '/api/auth/login/',
            json.dumps({'username': 'test_learner', 'password': 'wrong_password'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error']['code'], 'UNAUTHORIZED')

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(
            '/api/auth/login/',
            json.dumps({'username': 'test_learner'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_success(self):
        self.client.force_login(self.learner)
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)

    def test_logout_unauthenticated_returns_401(self):
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 401)


class SummaryTests(TestCase):
    def test_only_confirmed_learner_words_and_all_corrections(self):
        summary = make_summary([{'learner': 'chicken', 'reply': 'water', 'correction': {'explanation': 'Please use a polite request.', 'example': 'I would like chicken please.'}}])
        self.assertEqual(summary['used'], ['chicken'])
        self.assertIn('water', summary['unused'])
        self.assertEqual(len(summary['corrections']), 1)

