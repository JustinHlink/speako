from unittest.mock import patch
from .tests_confirmation import WorkflowFixture, GOOD
from .models import ApiUsage, Turn, Correction
from .providers import ProviderError

BAD = {**GOOD, 'reply': 'Would you like sparkling water?'}


class ReplyRecoveryTests(WorkflowFixture):
    @patch('practice.providers.reply')
    def test_off_list_candidate_is_rewritten_before_one_turn_is_saved(self, provider):
        usage = ApiUsage.objects.create(call_type='Reply', environment_id='test', reserved_usd=.02)
        provider.side_effect = [{**BAD, '_api_attempt_id': usage.pk}, GOOD]
        self.pending('I would like some water.')
        response = self.post('reply', pending_id='pending-1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(provider.call_count, 2)
        self.assertNotIn('sparkling', response.content.decode())
        self.assertEqual(Turn.objects.count(), 1)
        self.assertEqual(Turn.objects.get().learner_text, 'I would like some water.')
        self.assertFalse(Correction.objects.exists())
        usage.refresh_from_db()
        self.assertEqual(usage.status, 'Validation rejected')
        self.assertIn('words_to_replace', provider.call_args.args[0][0]['text'])

    @patch('practice.providers.reply', return_value=BAD)
    def test_second_invalid_candidate_stops_and_keeps_pending(self, provider):
        self.pending()
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 422)
        self.assertEqual(provider.call_count, 2)
        self.assertFalse(Turn.objects.exists())
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_id, 'pending-1')
        self.assertFalse(self.attempt.busy)

    @patch('practice.providers.reply')
    def test_rewrite_failure_or_budget_refusal_keeps_pending(self, provider):
        provider.side_effect = [BAD, ProviderError('Budget reached')]
        self.pending()
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 502)
        self.assertEqual(provider.call_count, 2)
        self.assertFalse(Turn.objects.exists())
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_id, 'pending-1')
        self.assertFalse(self.attempt.busy)

    @patch('practice.providers.reply')
    def test_off_topic_rewrite_redirects_without_false_correction(self, provider):
        provider.side_effect = [{**BAD, 'off_topic': True}, {**GOOD, 'off_topic': True}]
        self.pending('I like football.')
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 200)
        self.assertFalse(Correction.objects.exists())
        self.assertEqual(Turn.objects.count(), 1)

    @patch('practice.providers.reply', return_value=GOOD)
    def test_valid_reply_and_repeated_continue_need_only_one_call(self, provider):
        self.pending()
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 200)
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 200)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(Turn.objects.count(), 1)
