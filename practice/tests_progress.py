import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .models import Lesson, LessonAttempt, User
from .progress import map_status, map_statuses, latest_completed_attempt

REPLY = {'reply': 'Would you like water or tea?', 'correction_explanation': '',
         'corrected_example': '', 'off_topic': False}


def make_attempt(learner, lesson, status):
    ended = None if status == 'In progress' else timezone.now()
    return LessonAttempt.objects.create(learner=learner, lesson=lesson, status=status,
                                        opening_line='Hello!', ended_at=ended)


class MapStatusRuleTests(TestCase):
    """DR-03: Completed if any attempt is Completed, else In progress if any attempt exists, else Not started."""

    def setUp(self):
        self.restaurant = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.customs = Lesson.objects.create(scenario='Passing Customs', grammar_goal='Short answers.',
                                             turn_limit=5, status='Published')
        self.learner = User.objects.create_user(username='learner', password='pass', role='Learner')

    def test_lesson_without_attempts_is_not_started(self):
        self.assertEqual(map_status(self.learner, self.restaurant), 'Not started')

    def test_lesson_left_halfway_shows_in_progress(self):
        make_attempt(self.learner, self.restaurant, 'Exited')
        self.assertEqual(map_status(self.learner, self.restaurant), 'In progress')

    def test_completed_lesson_stays_completed_after_an_exited_retake(self):
        make_attempt(self.learner, self.restaurant, 'Completed')
        make_attempt(self.learner, self.restaurant, 'Exited')
        self.assertEqual(map_status(self.learner, self.restaurant), 'Completed')

    def test_each_lesson_gets_its_own_status(self):
        make_attempt(self.learner, self.restaurant, 'Completed')
        statuses = map_statuses(self.learner, [self.restaurant, self.customs])
        self.assertEqual(statuses, {self.restaurant.pk: 'Completed', self.customs.pk: 'Not started'})

    def test_latest_completed_attempt_is_the_one_to_reopen(self):
        self.assertIsNone(latest_completed_attempt(self.learner, self.restaurant))
        older = make_attempt(self.learner, self.restaurant, 'Completed')
        older.ended_at = timezone.now() - timedelta(days=1)
        older.save()
        latest = make_attempt(self.learner, self.restaurant, 'Completed')
        self.assertEqual(latest_completed_attempt(self.learner, self.restaurant), latest)


class AccountProgressTests(TestCase):
    """US-16 AC1 to AC3 through the sign-in, start and reply endpoints."""

    def setUp(self):
        self.restaurant = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.anna = User.objects.create_user(username='anna', password='anna-pass', role='Learner')
        self.ben = User.objects.create_user(username='ben', password='ben-pass', role='Learner')

    def post(self, url, data=None):
        return self.client.post(url, json.dumps(data or {}), content_type='application/json')

    def sign_in(self, username, password):
        self.assertEqual(self.post('/api/auth/login/', {'username': username, 'password': password}).status_code, 200)

    def sign_out(self):
        self.assertEqual(self.post('/api/auth/logout/').status_code, 204)

    def start(self):
        response = self.post('/api/start/', {'lesson_id': self.restaurant.id})
        self.assertEqual(response.status_code, 200)
        return response.json()['attempt']

    def answer(self, attempt_id, number):
        attempt = LessonAttempt.objects.get(pk=attempt_id)
        attempt.pending_transcript = 'I would like tea please'
        attempt.pending_id = f'{attempt_id}-{number}'
        attempt.save()
        return self.post('/api/reply/', {'attempt_id': attempt_id, 'pending_id': attempt.pending_id})

    @patch('practice.gemini.generate', return_value=REPLY)
    def test_completed_lesson_is_still_completed_after_signing_out_and_in(self, provider):
        self.sign_in('anna', 'anna-pass')
        attempt_id = self.start()['attempt_id']
        for number in range(1, self.restaurant.turn_limit + 1):
            self.assertEqual(self.answer(attempt_id, number).status_code, 200)
        self.sign_out()
        self.sign_in('anna', 'anna-pass')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.anna.pk)
        self.assertEqual(map_status(self.anna, self.restaurant), 'Completed')
        self.assertEqual(str(latest_completed_attempt(self.anna, self.restaurant).pk), attempt_id)

    @patch('practice.gemini.generate', return_value=REPLY)
    def test_lesson_left_halfway_shows_in_progress_and_restarts_at_the_first_turn(self, provider):
        self.sign_in('anna', 'anna-pass')
        first = self.start()
        self.assertEqual(self.answer(first['attempt_id'], 1).status_code, 200)
        self.assertEqual(map_status(self.anna, self.restaurant), 'In progress')

        second = self.start()
        self.assertEqual(second['turns'], [])
        self.assertEqual(second['status'], 'In progress')
        old = LessonAttempt.objects.get(pk=first['attempt_id'])
        self.assertEqual(old.status, 'Exited')
        self.assertEqual(old.turns.count(), 1)
        self.assertEqual(map_status(self.anna, self.restaurant), 'In progress')

    def test_second_learner_in_the_same_browser_sees_only_their_own_progress(self):
        anna_attempt = make_attempt(self.anna, self.restaurant, 'Completed')
        self.sign_in('anna', 'anna-pass')
        self.sign_out()
        self.sign_in('ben', 'ben-pass')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.ben.pk)
        self.assertEqual(map_status(self.ben, self.restaurant), 'Not started')
        self.assertIsNone(latest_completed_attempt(self.ben, self.restaurant))
        response = self.post('/api/reply/', {'attempt_id': str(anna_attempt.pk), 'pending_id': 'x'})
        self.assertEqual(response.status_code, 404)

    def test_signing_out_ends_access_to_the_lesson(self):
        self.sign_in('anna', 'anna-pass')
        attempt_id = self.start()['attempt_id']
        self.sign_out()
        response = self.post('/api/reply/', {'attempt_id': attempt_id, 'pending_id': 'x'})
        self.assertEqual(response.status_code, 401)


class SeedDemoUsersTests(TestCase):

    def seed(self, *args):
        call_command('seed_demo_users', *args, stdout=StringIO())

    def test_creates_one_account_per_role(self):
        self.seed('--password', 'demo-pass-123')
        roles = dict(User.objects.values_list('username', 'role'))
        self.assertEqual(roles, {'learner1': 'Learner', 'learner2': 'Learner',
                                 'curator1': 'Curator', 'reviewer1': 'Reviewer'})
        self.assertTrue(User.objects.get(username='learner1').check_password('demo-pass-123'))

    def test_running_again_resets_accounts_without_duplicates(self):
        self.seed('--password', 'demo-pass-123')
        User.objects.filter(username='curator1').update(role='Learner')
        self.seed('--password', 'new-pass-456')
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(User.objects.get(username='curator1').role, 'Curator')
        self.assertTrue(User.objects.get(username='reviewer1').check_password('new-pass-456'))

    def test_short_or_missing_password_creates_nothing(self):
        with patch.dict('os.environ', {'SPEAKO_DEMO_PASSWORD': ''}):
            with self.assertRaises(CommandError):
                self.seed()
            with self.assertRaises(CommandError):
                self.seed('--password', 'short')
        self.assertFalse(User.objects.exists())
