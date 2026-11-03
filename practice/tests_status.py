from django.test import TestCase

from . import gemini
from .models import ApiUsage


class UsageTests(TestCase):
    def test_usage_totals_read_current_ledger_fields(self):
        ApiUsage.objects.create(environment_id='test', call_type='Reply', estimated_usd=0.02, input_tokens=10, output_tokens=5)
        ApiUsage.objects.create(environment_id='test', call_type='Transcribe', estimated_usd=0.03, input_tokens=20, output_tokens=7)
        ledger = gemini.usage()
        self.assertEqual(ledger['attempts'], 2)
        self.assertEqual(ledger['guard_usd'], 0.05)
        self.assertEqual(ledger['prompt_tokens'], 30)
        self.assertEqual(ledger['output_tokens'], 12)

    def test_page_startup_endpoints_load(self):
        # app.js cannot finish loading, or enable Record, without /api/status/.
        status = self.client.get('/api/status/')
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()['usage']['attempts'], 0)
        self.assertEqual(self.client.get('/api/metrics/').status_code, 200)
