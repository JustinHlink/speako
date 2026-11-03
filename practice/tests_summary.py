from unittest.mock import patch
from django.test import Client
from .models import LessonAttempt, LessonSummary, Turn, User
from .tests_confirmation import GOOD, WorkflowFixture

CORRECTED = {**GOOD, 'correction_explanation': 'Use a polite request.', 'corrected_example': 'I would like tea.'}


@patch('practice.providers.reply', return_value=GOOD)
class SummaryTests(WorkflowFixture):
    def answer(self, text, key):
        self.attempt.refresh_from_db()
        self.pending(text, key)
        return self.post('reply', pending_id=key)

    def finish(self, text='I would like tea please'):
        for number in range(self.lesson.turn_limit):
            response = self.answer(text, f'turn-{self.attempt.pk}-{number}')
            self.assertEqual(response.status_code, 200)
        return response.json()['attempt']

    def status(self, client=None):
        return (client or self.client).get('/api/status/').json()

    def signed_in_again(self):
        client = Client()
        client.force_login(self.user)
        return client

    def test_last_turn_saves_used_and_unused_target_words(self, reply):
        attempt = self.finish()
        self.assertEqual(attempt['status'], 'Completed')
        self.assertEqual(attempt['summary']['used'], ['tea', 'please'])
        self.assertEqual(attempt['summary']['unused'], ['menu', 'chicken', 'rice', 'soup', 'water', 'bill'])

    def test_no_summary_before_the_last_turn(self, reply):
        self.answer('I would like tea', 'only-turn')
        self.assertFalse(LessonSummary.objects.exists())

    def test_words_in_ai_replies_do_not_count_as_used(self, reply):
        # GOOD replies say "water"; the learner never does.
        self.assertIn('water', self.finish()['summary']['unused'])

    def test_discarded_transcript_does_not_count_as_used(self, reply):
        self.pending('chicken', 'discarded')
        self.post('discard', pending_id='discarded')
        self.assertIn('chicken', self.finish()['summary']['unused'])

    def test_each_correction_is_listed_with_what_the_learner_said(self, reply):
        reply.side_effect = [CORRECTED, GOOD, CORRECTED, GOOD, GOOD]
        corrections = self.finish('I want tea')['summary']['corrections']
        self.assertEqual(len(corrections), 2)
        self.assertEqual(corrections[0], {'original': 'I want tea', 'explanation': 'Use a polite request.',
                                          'example': 'I would like tea.'})

    def test_no_corrections_gives_an_empty_list(self, reply):
        self.assertEqual(self.finish()['summary']['corrections'], [])

    def test_exit_creates_no_summary_and_lesson_stays_in_progress(self, reply):
        self.answer('I would like tea', 'only-turn')
        response = self.post('exit')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['attempt']['summary'])
        self.assertFalse(LessonSummary.objects.exists())
        self.assertEqual(self.status()['progress'], {'status': 'In progress', 'last_completed_attempt_id': None})

    def test_starting_again_abandons_old_attempt_without_summary(self, reply):
        self.answer('I would like tea', 'only-turn')
        response = self.client.post('/api/start/', {'lesson_id': self.lesson.pk}, content_type='application/json')
        self.assertEqual(response.json()['attempt']['turns'], [])
        self.assertFalse(LessonSummary.objects.exists())

    def test_failed_summary_write_does_not_complete_the_lesson(self, reply):
        for number in range(self.lesson.turn_limit - 1):
            self.answer('I would like tea', f'turn-{number}')
        self.attempt.refresh_from_db()
        self.pending('I would like tea', 'last-turn')
        self.client.raise_request_exception = False
        with patch('practice.views.save_summary', side_effect=RuntimeError):
            self.assertEqual(self.post('reply', pending_id='last-turn').status_code, 500)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, 'In progress')
        self.assertEqual(self.attempt.pending_id, 'last-turn')
        self.assertFalse(self.attempt.busy)
        self.assertFalse(Turn.objects.filter(pending_id='last-turn').exists())

    def test_repeated_final_request_keeps_one_summary(self, reply):
        self.finish()
        final_key = self.attempt.turns.order_by('-turn_number').first().pending_id
        self.assertEqual(self.post('reply', pending_id=final_key).status_code, 200)
        self.assertEqual(LessonSummary.objects.count(), 1)
        self.assertEqual(reply.call_count, self.lesson.turn_limit)

    def test_signing_back_in_shows_completed_with_saved_summary(self, reply):
        finished = self.finish()
        status = self.status(self.signed_in_again())
        self.assertEqual(status['progress'], {'status': 'Completed', 'last_completed_attempt_id': finished['attempt_id']})
        self.assertEqual(status['attempt']['summary'], finished['summary'])

    def test_summary_can_be_reopened_after_signing_back_in(self, reply):
        finished = self.finish()
        response = self.signed_in_again().get(f"/api/attempts/{finished['attempt_id']}/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary'], finished['summary'])

    def test_retake_left_unfinished_keeps_completed_and_its_summary(self, reply):
        finished = self.finish()
        self.attempt = LessonAttempt.objects.create(learner=self.user, lesson=self.lesson, opening_line='Hello!')
        self.answer('chicken', 'retake-turn')
        self.post('exit')
        status = self.status()
        self.assertIsNone(status['attempt']['summary'])
        self.assertEqual(status['progress'], {'status': 'Completed', 'last_completed_attempt_id': finished['attempt_id']})
        reopened = self.client.get(f"/api/attempts/{finished['attempt_id']}/summary/").json()['summary']
        self.assertEqual(reopened, finished['summary'])

    def test_unfinished_attempt_has_no_summary_to_reopen(self, reply):
        self.assertEqual(self.client.get(f'/api/attempts/{self.attempt.pk}/summary/').status_code, 404)

    def test_other_learner_cannot_reopen_or_see_progress(self, reply):
        finished = self.finish()
        other = Client()
        other.force_login(User.objects.create_user(username='other', password='test-pass'))
        self.assertEqual(other.get(f"/api/attempts/{finished['attempt_id']}/summary/").status_code, 404)
        self.assertEqual(self.status(other)['progress'], {'status': 'Not started', 'last_completed_attempt_id': None})

    def test_signed_out_request_is_denied(self, reply):
        finished = self.finish()
        self.assertEqual(Client().get(f"/api/attempts/{finished['attempt_id']}/summary/").status_code, 401)
