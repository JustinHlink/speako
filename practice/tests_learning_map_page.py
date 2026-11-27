from django.test import TestCase
from django.utils import timezone
from .models import User, Lesson, LessonAttempt, LessonWord, Turn, Flag, LessonSummary


class LearningMapPageTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(username='map-page-learner', password='password123', role='Learner')
        self.reviewer = User.objects.create_user(username='map-page-reviewer', password='password123', role='Reviewer')
        self.restaurant = Lesson.objects.get(scenario='Ordering at a Restaurant')
        self.customs = Lesson.objects.create(
            scenario='Passing Customs',
            grammar_goal='Short factual answers.',
            turn_limit=5,
            status='Published'
        )
        LessonWord.objects.create(lesson=self.customs, word='passport')

    def test_map_page_loads_with_signin_component_and_csrf_cookie(self):
        res = self.client.get('/map/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'sign-in-form')
        self.assertContains(res, 'map_page.js')
        self.assertIn('csrftoken', res.cookies)

    def test_map_page_displays_signed_in_user_and_reviewer_queue_link(self):
        self.client.force_login(self.learner)
        learner_page = self.client.get('/map/')
        self.assertContains(learner_page, 'Signed in as map-page-learner')

        self.client.force_login(self.reviewer)
        reviewer_page = self.client.get('/map/')
        self.assertContains(reviewer_page, 'Signed in as map-page-reviewer')
        self.assertContains(reviewer_page, 'Open review queue')

    def test_lessons_api_reflects_learner_progress_for_map_page(self):
        LessonAttempt.objects.create(
            learner=self.learner,
            lesson=self.restaurant,
            status='Completed',
            ended_at=timezone.now()
        )
        LessonAttempt.objects.create(
            learner=self.learner,
            lesson=self.customs,
            status='In progress'
        )
        self.client.force_login(self.learner)
        res = self.client.get('/api/lessons/')
        self.assertEqual(res.status_code, 200)
        by_scenario = {item['scenario']: item['status_on_map'] for item in res.json()['lessons']}
        self.assertEqual(by_scenario['Ordering at a Restaurant'], 'Completed')
        self.assertEqual(by_scenario['Passing Customs'], 'In progress')

    def test_reviewer_marked_incorrect_turn_is_flagged_in_summary_and_status(self):
        att = LessonAttempt.objects.create(
            learner=self.learner,
            lesson=self.restaurant,
            status='Completed',
            opening_line='Welcome!',
            ended_at=timezone.now()
        )
        t1 = Turn.objects.create(attempt=att, turn_number=1, learner_text='Menu please', ai_reply='Here it is', pending_id='rev-inc-1')
        t2 = Turn.objects.create(attempt=att, turn_number=2, learner_text='Tea please', ai_reply='Bad reply', pending_id='rev-inc-2')
        Flag.objects.create(turn=t1, status='Acceptable', reviewer=self.reviewer, reviewed_at=timezone.now())
        Flag.objects.create(turn=t2, status='Incorrect', reviewer=self.reviewer, reviewed_at=timezone.now())
        LessonSummary.objects.create(attempt=att, words_used=['menu', 'tea'], words_not_used=[])

        self.client.force_login(self.learner)
        res = self.client.get(f'/api/attempts/{att.id}/summary/')
        self.assertEqual(res.status_code, 200)
        turns = res.json()['attempt']['turns']
        self.assertFalse(turns[0]['review_incorrect'])
        self.assertEqual(turns[0]['flag_status'], 'Acceptable')
        self.assertTrue(turns[1]['review_incorrect'])
        self.assertEqual(turns[1]['flag_status'], 'Incorrect')
