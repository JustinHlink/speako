import io
import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from .gemini import ProviderError
from .models import ApiUsage, Lesson, LessonWord, LessonAttempt, Turn, User, SharedBeginnerWord
from .vocabulary import allowed_words, lesson_is_configured, outside_words

class VocabularyTests(TestCase):

    def setUp(self):
        self.restaurant = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.customs = Lesson.objects.create(
            scenario='Passing Customs',
            grammar_goal='Answer simple questions politely.',
            turn_limit=5,
            status='Published',
        )
        LessonWord.objects.create(lesson=self.customs, word='Passport')

    def test_lesson_allows_its_own_words_and_shared_beginner_words(self):
        allowed = allowed_words(self.restaurant)
        self.assertIn('chicken', allowed)
        self.assertIn('hello', allowed)

    def test_reply_using_only_allowed_words_passes(self):
        reply = "Hello! I'd like to recommend the chicken soup."
        self.assertEqual(outside_words(reply, self.restaurant), [])

    def test_reply_with_off_list_words_is_caught(self):
        reply = 'Would you like quantum physics?'
        self.assertEqual(outside_words(reply, self.restaurant), ['physics', 'quantum'])

    def test_each_lesson_has_its_own_word_list(self):
        reply = 'Can I have your passport please?'
        self.assertEqual(outside_words(reply, self.customs), [])
        self.assertEqual(outside_words(reply, self.restaurant), ['passport'])

    def test_published_lesson_with_words_can_start(self):
        self.assertTrue(lesson_is_configured(self.restaurant))

    def test_lesson_without_word_list_cannot_start(self):
        empty = Lesson.objects.create(
            scenario='Asking for Directions',
            grammar_goal='Ask the way politely.',
            turn_limit=5,
            status='Published',
        )
        self.assertFalse(lesson_is_configured(empty))

    def test_draft_lesson_or_bad_turn_limit_cannot_start(self):
        self.customs.status = 'Draft'
        self.assertFalse(lesson_is_configured(self.customs))
        self.customs.status = 'Published'
        self.customs.turn_limit = 31
        self.assertFalse(lesson_is_configured(self.customs))


GOOD_REPLY = {'reply': 'Would you like water or tea?', 'correction_explanation': '',
              'corrected_example': '', 'off_topic': False}
OFF_LIST_REPLY = {'reply': 'Would you like quantum physics?', 'correction_explanation': '',
                  'corrected_example': '', 'off_topic': False}


class VocabularyEndpointTests(TestCase):

    def setUp(self):
        self.restaurant = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.learner = User.objects.create_user(username='learner', password='pass', role='Learner')
        self.client.force_login(self.learner)

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')

    def start(self, lesson):
        return self.post('/api/start/', {'lesson_id': lesson.id})

    def started_attempt(self, transcript='I would like chicken please'):
        self.assertEqual(self.start(self.restaurant).status_code, 200)
        attempt = LessonAttempt.objects.get(learner=self.learner, status='In progress')
        attempt.pending_transcript = transcript
        attempt.pending_id = 'pending-1'
        attempt.save()
        return attempt

    def reply(self, attempt, pending_id='pending-1'):
        return self.post('/api/reply/', {'attempt_id': str(attempt.id), 'pending_id': pending_id})

    def test_lesson_without_word_list_does_not_start(self):
        empty = Lesson.objects.create(scenario='Asking for Directions', grammar_goal='Ask the way politely.',
                                      turn_limit=5, status='Published')
        response = self.start(empty)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'LESSON_UNAVAILABLE')
        self.assertFalse(LessonAttempt.objects.exists())

    def test_draft_lesson_does_not_start(self):
        self.restaurant.status = 'Draft'
        self.restaurant.save()
        self.assertEqual(self.start(self.restaurant).status_code, 409)
        self.assertFalse(LessonAttempt.objects.exists())

    def test_configured_lesson_starts_with_an_opening_inside_the_word_list(self):
        response = self.start(self.restaurant)
        self.assertEqual(response.status_code, 200)
        attempt = response.json()['attempt']
        self.assertEqual(attempt['status'], 'In progress')
        self.assertEqual(attempt['turn_limit'], 5)
        self.assertEqual(outside_words(attempt['opening'], self.restaurant), [])

    def test_lesson_does_not_start_when_opening_line_is_outside_word_list(self):
        SharedBeginnerWord.objects.filter(word='welcome').delete()
        response = self.start(self.restaurant)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'LESSON_UNAVAILABLE')
        self.assertFalse(LessonAttempt.objects.exists())
    
    def test_starting_again_exits_the_old_attempt(self):
        self.start(self.restaurant)
        self.start(self.restaurant)
        self.assertEqual(LessonAttempt.objects.filter(status='In progress').count(), 1)
        self.assertEqual(LessonAttempt.objects.filter(status='Exited').count(), 1)

    def test_signed_out_user_cannot_start(self):
        self.client.logout()
        self.assertEqual(self.start(self.restaurant).status_code, 401)

    @patch('practice.gemini.generate', return_value=GOOD_REPLY)
    def test_prompt_lists_the_allowed_words(self, provider):
        attempt = self.started_attempt()
        self.reply(attempt)
        system_prompt = provider.call_args.args[2]
        self.assertIn('chicken', system_prompt)
        self.assertIn('hello', system_prompt)

    @patch('practice.gemini.generate', return_value=GOOD_REPLY)
    def test_reply_inside_the_word_list_is_saved(self, provider):
        attempt = self.started_attempt()
        response = self.reply(attempt)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt']['turns'][0]['reply'], 'Would you like water or tea?')
        attempt.refresh_from_db()
        self.assertEqual(attempt.pending_transcript, '')
        self.assertEqual(attempt.turns.count(), 1)

    @patch('practice.gemini.generate')
    def test_reply_outside_the_word_list_is_hidden_and_turn_does_not_advance(self, provider):
        usage = ApiUsage.objects.create(environment_id='test', call_type='Reply')
        provider.return_value = {**OFF_LIST_REPLY, '_api_attempt_id': usage.pk}
        attempt = self.started_attempt()
        response = self.reply(attempt)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'VOCABULARY_REJECTED')
        self.assertNotIn('quantum', response.content.decode())
        attempt.refresh_from_db()
        self.assertEqual(attempt.turns.count(), 0)
        self.assertEqual(attempt.pending_transcript, 'I would like chicken please')
        self.assertFalse(attempt.busy)
        usage.refresh_from_db()
        self.assertEqual(usage.status, 'Validation rejected')

    @patch('practice.gemini.generate', return_value={
        'reply': 'Good try.', 'correction_explanation': 'Use "I would like" to ask politely.',
        'corrected_example': 'I would like quantum soup.', 'off_topic': False})
    def test_corrected_example_outside_the_word_list_is_rejected(self, provider):
        attempt = self.started_attempt()
        self.assertEqual(self.reply(attempt).status_code, 422)
        self.assertFalse(Turn.objects.exists())

    @patch('practice.gemini.generate', side_effect=ProviderError('quota reached'))
    def test_provider_failure_keeps_the_transcript(self, provider):
        attempt = self.started_attempt()
        self.assertEqual(self.reply(attempt).status_code, 502)
        attempt.refresh_from_db()
        self.assertEqual(attempt.pending_transcript, 'I would like chicken please')
        self.assertFalse(attempt.busy)

    @patch('practice.gemini.generate', return_value=GOOD_REPLY)
    def test_retrying_an_accepted_transcript_does_not_call_the_ai_twice(self, provider):
        attempt = self.started_attempt()
        first = self.reply(attempt)
        second = self.reply(attempt)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(Turn.objects.count(), 1)

    @patch('practice.gemini.generate', return_value=GOOD_REPLY)
    def test_last_turn_completes_the_attempt(self, provider):
        attempt = self.started_attempt()
        for number in range(1, self.restaurant.turn_limit + 1):
            attempt.refresh_from_db()
            attempt.pending_transcript = 'I would like tea please'
            attempt.pending_id = f'pending-{number}'
            attempt.save()
            self.assertEqual(self.reply(attempt, f'pending-{number}').status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'Completed')
        self.assertIsNotNone(attempt.ended_at)

    def fake_gemini(self, network, reply):
        body = {'usageMetadata': {'promptTokenCount': 900, 'candidatesTokenCount': 30},
                'candidates': [{'content': {'parts': [{'text': json.dumps(reply)}]}}]}
        network.return_value.__enter__.return_value = io.BytesIO(json.dumps(body).encode())

    @override_settings(GEMINI_API_KEY='test-only', GEMINI_FREE_TIER_CONFIRMED=True, GEMINI_MODEL='gemini-3.1-flash-lite')
    @patch('urllib.request.urlopen')
    def test_reply_works_through_gemini_client_without_a_real_call(self, network):
        self.fake_gemini(network, GOOD_REPLY)
        attempt = self.started_attempt()
        response = self.reply(attempt)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt']['turns'][0]['reply'], GOOD_REPLY['reply'])
        usage = ApiUsage.objects.get()
        self.assertEqual((usage.call_type, usage.status), ('Reply', 'Success'))
        self.assertEqual(self.client.get('/api/status/').status_code, 200)

    @override_settings(GEMINI_API_KEY='test-only', GEMINI_FREE_TIER_CONFIRMED=True, GEMINI_MODEL='gemini-3.1-flash-lite')
    @patch('urllib.request.urlopen')
    def test_off_list_reply_through_gemini_client_is_rejected_and_logged(self, network):
        self.fake_gemini(network, OFF_LIST_REPLY)
        attempt = self.started_attempt()
        self.assertEqual(self.reply(attempt).status_code, 422)
        self.assertFalse(Turn.objects.exists())
        self.assertEqual(ApiUsage.objects.get().status, 'Validation rejected')