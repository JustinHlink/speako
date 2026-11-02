"""Budget regression tests for the current ApiUsage schema."""
import io
import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from .models import ApiUsage
from .gemini import generate, ProviderError

@override_settings(GEMINI_API_KEY='test-only-not-a-real-key', GEMINI_FREE_TIER_CONFIRMED=True, GEMINI_MODEL='gemini-3.1-flash-lite', PROJECT_BUDGET_USD=10, RECORDED_EXTERNAL_SPEND_USD=0)
class BudgetTests(TestCase):
    @patch('urllib.request.urlopen')
    def test_success_records_new_usage_fields(self, network):
        payload = {'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 8},
                   'candidates': [{'content': {'parts': [{'text': '{"transcript":"tea"}'}]}}]}
        network.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
        result = generate('transcription', [], '', {})
        row = ApiUsage.objects.get()
        self.assertEqual(result['transcript'], 'tea')
        self.assertEqual(row.call_type, 'Transcribe')
        self.assertEqual(row.status, 'Success')
        self.assertEqual(row.input_tokens, 12)
        self.assertEqual(row.output_tokens, 8)
        self.assertIsNotNone(row.finished_at)

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
        self.assertEqual(attempt.status, 'Unknown')
        self.assertEqual(attempt.reserved_usd, 0.02)

    @override_settings(GEMINI_FREE_TIER_CONFIRMED=False)
    @patch('urllib.request.urlopen')
    def test_no_api_until_free_project_confirmed(self, network):
        with self.assertRaises(ProviderError):
            generate('conversation', [], '', {})
        network.assert_not_called()
