import io
import json
import urllib.error
from unittest.mock import patch
from django.test import TestCase, override_settings
from .gemini import generate, ProviderError
from .models import ApiUsage

@override_settings(GEMINI_API_KEY='test-only',GEMINI_FREE_TIER_CONFIRMED=True,GEMINI_MODEL='gemini-3.1-flash-lite',PROJECT_BUDGET_USD=10,RECORDED_EXTERNAL_SPEND_USD=0,MAX_API_ATTEMPTS=500)
class SpeechRetryTests(TestCase):
    def response(self):
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':'{"transcript":"water"}'}]}}]}).encode())

    @patch('practice.gemini.time.sleep')
    @patch('urllib.request.urlopen')
    def test_transient_http_error_retries_once_and_keeps_both_reservations(self, network, sleep):
        network.side_effect=[urllib.error.HTTPError('redacted',503,'Unavailable',{},None),self.response()]
        self.assertEqual(generate('transcription',[],'',{})['transcript'],'water')
        self.assertEqual(list(ApiUsage.objects.values_list('status',flat=True)),['Unknown','Success'])
        self.assertEqual(network.call_count,2)
        self.assertEqual(network.call_args.kwargs['timeout'],12)
        sleep.assert_called_once_with(0.5)

    @patch('practice.gemini.time.sleep')
    @patch('urllib.request.urlopen',side_effect=TimeoutError)
    def test_timeout_has_only_two_attempts(self, network, sleep):
        with self.assertRaises(ProviderError):generate('transcription',[],'',{})
        self.assertEqual(network.call_count,2)
        self.assertEqual(ApiUsage.objects.count(),2)

    @patch('practice.gemini.time.sleep')
    @patch('urllib.request.urlopen')
    def test_retry_must_pass_budget_guard(self, network, sleep):
        network.side_effect=TimeoutError
        with override_settings(PROJECT_BUDGET_USD=0.03):
            with self.assertRaisesMessage(ProviderError,'usage guard'):generate('transcription',[],'',{})
        self.assertEqual(network.call_count,1)
        self.assertEqual(ApiUsage.objects.count(),1)

    @patch('urllib.request.urlopen')
    def test_quota_key_and_format_errors_do_not_retry(self, network):
        for code in [400,403,404,429]:
            with self.subTest(code=code):
                network.reset_mock()
                network.side_effect=urllib.error.HTTPError('redacted',code,'Error',{},None)
                with self.assertRaises(ProviderError) as failure:generate('transcription',[],'',{})
                self.assertEqual(failure.exception.http_status,code)
                self.assertEqual(network.call_count,1)

    @patch('urllib.request.urlopen',side_effect=TimeoutError)
    def test_conversation_failure_does_not_silently_multiply_reply_calls(self, network):
        with self.assertRaises(ProviderError):generate('conversation',[],'',{})
        self.assertEqual(network.call_count,1)
