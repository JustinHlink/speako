import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import User, Lesson, LessonAttempt, Turn, Correction, LessonSummary
from .providers import ProviderError

GOOD = {'reply': 'Would you like water?', 'correction_explanation': '',
        'corrected_example': '', 'off_topic': False}


class WorkflowFixture(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='test-pass')
        self.client.force_login(self.user)
        self.lesson = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.attempt = LessonAttempt.objects.create(learner=self.user, lesson=self.lesson,
                                                   opening_line='Hello!')

    def post(self, path, **data):
        return self.client.post('/api/' + path + '/', json.dumps(
            {'attempt_id': str(self.attempt.pk), **data}), content_type='application/json')

    def audio(self, content=b'audio', mime='audio/webm', **fields):
        return self.client.post('/api/transcribe/', {
            'attempt_id': str(self.attempt.pk),
            'audio': SimpleUploadedFile('answer.webm', content, content_type=mime), **fields})

    def pending(self, text='I would like tea.', key='pending-1'):
        self.attempt.pending_transcript = text
        self.attempt.pending_id = key
        self.attempt.save()


class ConfirmationTests(WorkflowFixture):
    @patch('practice.providers.reply')
    @patch('practice.providers.transcribe', return_value={'transcript': 'I would likes tea.'})
    def test_recognition_is_pending_and_verbatim_until_continue(self, recognition, reply):
        response = self.audio()
        self.assertEqual(response.status_code, 200)
        pending = response.json()['attempt']['pending']
        self.assertEqual(pending['text'], 'I would likes tea.')
        self.assertTrue(pending['id'])
        self.assertFalse(Turn.objects.exists())
        self.assertFalse(Correction.objects.exists())
        reply.assert_not_called()
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.busy)

    @patch('practice.providers.reply', return_value=GOOD)
    @patch('practice.providers.transcribe', return_value={'transcript': 'I would like tea.'})
    def test_continue_evaluates_only_confirmed_text(self, recognition, reply):
        key = self.audio().json()['attempt']['pending']['id']
        self.assertEqual(self.post('reply', pending_id=key).status_code, 200)
        self.assertEqual(Turn.objects.get().learner_text, 'I would like tea.')
        reply.assert_called_once()

    @patch('practice.providers.reply')
    def test_try_again_drops_text_without_evaluation_or_history(self, reply):
        self.pending('misheard words')
        self.assertEqual(self.post('discard', pending_id='pending-1').status_code, 200)
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 409)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_transcript, '')
        self.assertEqual(self.attempt.pending_id, '')
        self.assertFalse(Turn.objects.exists())
        self.assertFalse(Correction.objects.exists())
        self.assertFalse(LessonSummary.objects.exists())
        reply.assert_not_called()

    @patch('practice.providers.reply', return_value=GOOD)
    @patch('practice.providers.transcribe', return_value={'transcript': 'I would like tea.'})
    def test_discarded_text_is_not_sent_in_next_reply_context(self, recognition, reply):
        self.pending('misheard words')
        self.post('discard', pending_id='pending-1')
        key = self.audio().json()['attempt']['pending']['id']
        self.post('reply', pending_id=key)
        context = json.loads(reply.call_args.args[0][0]['text'])
        self.assertEqual(context['history'], [])
        self.assertNotIn('misheard', json.dumps(context))

    @patch('practice.providers.reply')
    @patch('practice.providers.transcribe', return_value={'transcript': ''})
    def test_silence_does_not_evaluate_or_advance(self, recognition, reply):
        response = self.audio()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'NO_SPEECH')
        self.assertFalse(Turn.objects.exists())
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.pending_id)
        self.assertFalse(self.attempt.busy)
        reply.assert_not_called()

    @patch('practice.providers.transcribe', side_effect=ProviderError('Unavailable'))
    def test_recognition_failure_unlocks_attempt_for_retry(self, recognition):
        self.assertEqual(self.audio().status_code, 502)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.busy)
        self.assertFalse(self.attempt.pending_id)
        self.assertFalse(Turn.objects.exists())

    @patch('practice.providers.transcribe', return_value={'transcript': 123})
    def test_malformed_transcript_is_not_saved(self, recognition):
        self.assertEqual(self.audio().status_code, 502)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.pending_id)

    @patch('practice.providers.transcribe')
    def test_audio_validation_before_provider_call(self, recognition):
        self.assertEqual(self.audio(b'').status_code, 400)
        self.assertEqual(self.audio(mime='text/plain').status_code, 415)
        self.assertEqual(self.audio(b'x' * (4 * 1024 * 1024 + 1)).status_code, 413)
        recognition.assert_not_called()

    @patch('practice.providers.transcribe')
    def test_pending_text_cannot_be_replaced_without_discard(self, recognition):
        self.pending()
        self.assertEqual(self.audio().status_code, 409)
        recognition.assert_not_called()

    def test_stale_discard_does_not_delete_newer_text(self):
        self.pending(key='newer-id')
        self.assertEqual(self.post('discard', pending_id='old-id').status_code, 409)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_id, 'newer-id')

    @patch('practice.providers.transcribe')
    def test_other_learner_cannot_read_or_change_attempt(self, recognition):
        self.pending()
        other = User.objects.create_user(username='other', password='test-pass')
        self.client.force_login(other)
        self.assertIsNone(self.client.get('/api/status/').json()['attempt'])
        self.assertEqual(self.audio().status_code, 404)
        self.assertEqual(self.post('discard', pending_id='pending-1').status_code, 404)
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 404)
        recognition.assert_not_called()

    def test_signed_out_and_wrong_role_requests_are_denied(self):
        self.client.logout()
        self.assertEqual(self.audio().status_code, 401)
        self.user.role = 'Reviewer'
        self.user.save()
        self.client.force_login(self.user)
        self.assertEqual(self.audio().status_code, 403)
        self.assertEqual(self.post('discard', pending_id='x').status_code, 403)

    def test_busy_and_closed_attempts_do_not_discard_pending_text(self):
        self.pending()
        self.attempt.busy = True
        self.attempt.save()
        self.assertEqual(self.post('discard', pending_id='pending-1').status_code, 409)
        self.attempt.busy = False
        self.attempt.status = 'Exited'
        self.attempt.save()
        self.assertEqual(self.audio().status_code, 409)

    def test_pending_survives_page_reload(self):
        self.pending()
        data = self.client.get('/api/status/').json()
        self.assertEqual(data['attempt']['pending']['text'], 'I would like tea.')

    def test_exit_clears_pending_without_creating_summary(self):
        self.pending()
        self.assertEqual(self.post('exit').status_code, 200)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, 'Exited')
        self.assertFalse(self.attempt.pending_id)
        self.assertFalse(LessonSummary.objects.exists())

    def test_csrf_is_required(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/api/discard/').status_code, 403)


class CorrectionTests(WorkflowFixture):
    @patch('practice.providers.reply', return_value={
        **GOOD, 'correction_explanation': 'Use a polite request.',
        'corrected_example': 'I would like tea please.'})
    def test_targeted_correction_is_saved_with_confirmed_turn(self, reply):
        self.pending('I would likes tea.')
        response = self.post('reply', pending_id='pending-1')
        self.assertEqual(response.status_code, 200)
        correction = Correction.objects.get()
        self.assertEqual(correction.turn.learner_text, 'I would likes tea.')
        self.assertEqual(response.json()['attempt']['turns'][0]['correction']['example'],
                         'I would like tea please.')
        self.assertIn(self.lesson.grammar_goal, reply.call_args.args[1])

    @patch('practice.providers.reply', return_value=GOOD)
    def test_correct_answer_creates_no_correction(self, reply):
        self.pending()
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 200)
        self.assertFalse(Correction.objects.exists())

    @patch('practice.providers.reply', return_value={**GOOD, 'off_topic': True})
    def test_correct_off_topic_text_gets_redirection_without_correction(self, reply):
        self.pending('I like football.')
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 200)
        self.assertFalse(Correction.objects.exists())
        self.assertEqual(Turn.objects.get().ai_reply, GOOD['reply'])

    @patch('practice.providers.reply', return_value={
        **GOOD, 'off_topic': True, 'correction_explanation': 'Wrong.',
        'corrected_example': 'I would like tea.'})
    def test_off_topic_output_with_false_correction_is_rejected(self, reply):
        self.pending('I like football.')
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 422)
        self.assertFalse(Turn.objects.exists())
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.pending_id, 'pending-1')

    @patch('practice.providers.reply', side_effect=ProviderError('Unavailable'))
    def test_reply_failure_preserves_transcript(self, reply):
        self.pending()
        self.assertEqual(self.post('reply', pending_id='pending-1').status_code, 502)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.busy)
        self.assertEqual(self.attempt.pending_id, 'pending-1')
