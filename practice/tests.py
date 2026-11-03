"""Budget regression tests for the current ApiUsage schema."""
import io
import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import ApiUsage, LessonAttempt, Lesson, User, LessonWord
from .lesson import LESSON, make_summary
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

class LearningMapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.learner = User.objects.create_user(username='map_student', password='password', role='Learner')
        
        self.lesson1 = Lesson.objects.create(scenario='Restaurant', grammar_goal='Polite requests', turn_limit=5, status='Published')
        LessonWord.objects.create(lesson=self.lesson1, word='water')
        LessonWord.objects.create(lesson=self.lesson1, word='menu')
        
        self.lesson2 = Lesson.objects.create(scenario='Customs', grammar_goal='Short answers', turn_limit=5, status='Published')
        
        LessonAttempt.objects.create(learner=self.learner, lesson=self.lesson1, status='Completed')

    def test_list_lessons_status_computation(self):
        self.client.force_login(self.learner)
        response = self.client.get('/api/lessons/')
        self.assertEqual(response.status_code, 200)
        
        lessons = response.json()['lessons']
        # Migration 0002 also seeds the restaurant lesson, so count Published lessons instead of fixing 2.
        self.assertEqual(len(lessons), Lesson.objects.filter(status='Published').count())

        l1_data = next(l for l in lessons if l['id'] == self.lesson1.id)
        self.assertEqual(l1_data['status_on_map'], 'Completed')
        
        l2_data = next(l for l in lessons if l['id'] == self.lesson2.id)
        self.assertEqual(l2_data['status_on_map'], 'Not started')

    def test_get_lesson_detail_success(self):
        self.client.force_login(self.learner)
        response = self.client.get(f'/api/lessons/{self.lesson1.id}/')
        self.assertEqual(response.status_code, 200)
        
        lesson_data = response.json()['lesson']
        self.assertEqual(lesson_data['scenario'], 'Restaurant')
        self.assertIn('water', lesson_data['target_words'])
        self.assertIsNotNone(lesson_data['last_completed_attempt_id'])

    def test_list_lessons_in_progress_status(self):
        LessonAttempt.objects.create(
            learner=self.learner,
            lesson=self.lesson2,
            status='In progress'
        )

        self.client.force_login(self.learner)
        response = self.client.get('/api/lessons/')
        self.assertEqual(response.status_code, 200)

        lessons = response.json()['lessons']
        l2_data = next(l for l in lessons if l['id'] == self.lesson2.id)
        
        self.assertEqual(l2_data['status_on_map'], 'In progress')

    def test_list_lessons_exited_status_returns_in_progress(self):
        LessonAttempt.objects.create(
            learner=self.learner,
            lesson=self.lesson2,
            status='Exited'
        )

        self.client.force_login(self.learner)
        response = self.client.get('/api/lessons/')
        self.assertEqual(response.status_code, 200)

        lessons = response.json()['lessons']
        l2_data = next(l for l in lessons if l['id'] == self.lesson2.id)
        
        self.assertEqual(l2_data['status_on_map'], 'In progress')

    def test_list_lessons_unauthenticated_returns_401(self):
        response = self.client.get('/api/lessons/')
        self.assertEqual(response.status_code, 401)
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

    def test_register_success(self):
        response = self.client.post(
            '/api/auth/register/',
            json.dumps({'username': 'new_student', 'password': 'password123', 'role': 'Learner'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='new_student').exists())
        self.assertEqual(User.objects.get(username='new_student').role, 'Learner')

    def test_register_duplicate_username_returns_409(self):
        response = self.client.post(
            '/api/auth/register/',
            json.dumps({'username': 'test_learner', 'password': 'password123'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 409)

    def test_register_ignores_requested_role_and_forces_learner(self):
        response = self.client.post(
            '/api/auth/register/',
            json.dumps({'username': 'hacker_user', 'password': 'password123', 'role': 'Curator'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        user = User.objects.get(username='hacker_user')
        self.assertEqual(user.role, 'Learner')
        self.assertNotEqual(user.role, 'Curator')

    def test_login_and_register_with_whitespace_password(self):
        spaced_password = "  secret password 123  "
        
        reg_response = self.client.post(
            '/api/auth/register/',
            json.dumps({
                'username': 'whitespace_user',
                'password': spaced_password
            }),
            content_type='application/json'
        )
        self.assertEqual(reg_response.status_code, 201)

        self.client.post('/api/auth/logout/')

        wrong_login_response = self.client.post(
            '/api/auth/login/',
            json.dumps({
                'username': 'whitespace_user',
                'password': 'secret password 123'
            }),
            content_type='application/json'
        )
        self.assertEqual(wrong_login_response.status_code, 401)

        correct_login_response = self.client.post(
            '/api/auth/login/',
            json.dumps({
                'username': 'whitespace_user',
                'password': spaced_password
            }),
            content_type='application/json'
        )
        self.assertEqual(correct_login_response.status_code, 200)

    def test_login_non_string_password_returns_400(self):
        response = self.client.post(
            '/api/auth/login/',
            json.dumps({
                'username': 'test_learner',
                'password': 12345
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class SummaryTests(TestCase):
    def test_only_confirmed_learner_words_and_all_corrections(self):
        summary = make_summary([{'learner': 'chicken', 'reply': 'water', 'correction': {'explanation': 'Please use a polite request.', 'example': 'I would like chicken please.'}}])
        self.assertEqual(summary['used'], ['chicken'])
        self.assertIn('water', summary['unused'])
        self.assertEqual(len(summary['corrections']), 1)

