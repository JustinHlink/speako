import json
from django.test import TestCase
from .models import User, Lesson, LessonAttempt, Turn, Flag

class FlagInputTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user(username='flag-owner', role='Learner')
        self.other = User.objects.create_user(username='flag-other', role='Learner')
        self.reviewer = User.objects.create_user(username='flag-reviewer', role='Reviewer')
        lesson = Lesson.objects.create(scenario='Restaurant', grammar_goal='Requests',turn_limit=5,status='Published')
        attempt = LessonAttempt.objects.create(learner=self.learner,lesson=lesson,status='In progress')
        self.turn = Turn.objects.create(attempt=attempt,turn_number=1,learner_text='water',ai_reply='Here is water.',pending_id='flag-probe')

    def test_bad_json_is_400_without_creating_flag(self):
        self.client.force_login(self.learner)
        for payload in ['', '{', '[]', 'null', '"text"']:
            with self.subTest(payload=payload):
                result = self.client.post('/api/flag/submit/',data=payload,content_type='application/json')
                self.assertEqual(result.status_code,400)
        self.assertFalse(Flag.objects.exists())

    def test_invalid_ids_are_400_for_both_endpoints(self):
        for value in ['abc', [1], True, 1.5, -1, 2**80]:
            with self.subTest(value=value):
                self.client.force_login(self.learner)
                self.assertEqual(self.client.post('/api/flag/submit/',data=json.dumps({'turn_id':value}),content_type='application/json').status_code,400)
                self.client.force_login(self.reviewer)
                self.assertEqual(self.client.post('/api/flag/review/',data=json.dumps({'flag_id':value,'status':'Acceptable'}),content_type='application/json').status_code,400)

    def test_ownership_duplicate_and_review_replay(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json').status_code,404)
        self.client.force_login(self.learner)
        first = self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json')
        self.assertEqual(first.status_code,201)
        self.assertEqual(self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json').status_code,409)
        self.client.force_login(self.reviewer)
        flag_id = first.json()['flag']['id']
        self.assertEqual(self.client.post('/api/flag/review/',{'flag_id':flag_id,'status':'Acceptable'},content_type='application/json').status_code,200)
        flag = Flag.objects.get(pk=flag_id)
        timestamp = flag.reviewed_at
        self.assertEqual(self.client.post('/api/flag/review/',{'flag_id':flag_id,'status':'Incorrect'},content_type='application/json').status_code,409)
        flag.refresh_from_db()
        self.assertEqual(flag.status,'Acceptable')
        self.assertEqual(flag.reviewed_at,timestamp)
        self.assertEqual(Flag.objects.count(),1)
