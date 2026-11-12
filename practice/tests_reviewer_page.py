from django.test import TestCase, Client
from .models import User, Lesson, LessonAttempt, LessonWord, Turn, Flag, Correction

class ReviewerPageTests(TestCase):
    def setUp(self):
        self.reviewer=User.objects.create_user(username='queue-reviewer',role='Reviewer')
        self.learner=User.objects.create_user(username='queue-learner')
        lesson=Lesson.objects.create(scenario='Review context',grammar_goal='Polite requests',turn_limit=5,status='Published')
        LessonWord.objects.create(lesson=lesson,word='water')
        self.attempt=LessonAttempt.objects.create(learner=self.learner,lesson=lesson,opening_line='Hello!')
        Turn.objects.create(attempt=self.attempt,turn_number=1,learner_text='Hello.',ai_reply='Would you like water?',pending_id='queue-first')
        turn=Turn.objects.create(attempt=self.attempt,turn_number=2,learner_text='I likes water.',ai_reply='Here is water.',pending_id='queue-flagged')
        Correction.objects.create(turn=turn,explanation='Use like after I.',corrected_example='I like water.')
        self.flag=Flag.objects.create(turn=turn)

    def test_page_and_apis_require_reviewer_role(self):
        self.assertEqual(self.client.get('/review/').status_code,401)
        for role in ['Learner','Curator']:
            user=User.objects.create_user(username='denied-'+role,role=role);self.client.force_login(user)
            self.assertEqual(self.client.get('/review/').status_code,403)
            self.assertEqual(self.client.get('/api/flag/list/').status_code,403)
            self.assertEqual(self.client.post('/api/flag/review/',{'flag_id':self.flag.pk,'status':'Incorrect'},content_type='application/json').status_code,403)
        self.flag.refresh_from_db();self.assertEqual(self.flag.status,'Unresolved')
        self.client.force_login(self.reviewer)
        page=self.client.get('/review/');self.assertEqual(page.status_code,200)
        self.assertContains(page,'reviewer.js');self.assertIn('csrftoken',page.cookies)

    def test_queue_contains_context_and_saved_decision_removes_item(self):
        self.client.force_login(self.reviewer)
        item=self.client.get('/api/flag/list/').json()['flags'][0]
        self.assertEqual(item['grammar_goal'],'Polite requests');self.assertEqual(item['target_words'],['water'])
        self.assertEqual(item['history'],[{'learner_text':'Hello.','ai_reply':'Would you like water?'}])
        self.assertEqual(item['correction']['example'],'I like water.')
        self.assertEqual(item['learner_text'],'I likes water.');self.assertEqual(item['opening'],'Hello!')
        self.assertTrue(item['flagged_at'])
        result=self.client.post('/api/flag/review/',{'flag_id':self.flag.pk,'status':'Incorrect'},content_type='application/json')
        self.assertEqual(result.status_code,200)
        self.flag.refresh_from_db();self.assertEqual(self.flag.reviewer,self.reviewer);self.assertIsNotNone(self.flag.reviewed_at)
        self.assertEqual(self.client.get('/api/flag/list/').json()['flags'],[])
        second=self.client.post('/api/flag/review/',{'flag_id':self.flag.pk,'status':'Acceptable'},content_type='application/json')
        self.assertEqual(second.status_code,409);self.flag.refresh_from_db();self.assertEqual(self.flag.status,'Incorrect')

    def test_csrf_is_enforced_for_browser_decisions(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.reviewer)
        response=client.get('/review/');token=response.cookies['csrftoken'].value
        payload={'flag_id':self.flag.pk,'status':'Acceptable'}
        self.assertEqual(client.post('/api/flag/review/',payload,content_type='application/json').status_code,403)
        self.assertEqual(client.post('/api/flag/review/',payload,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,200)

    def test_reviewer_link_visible_only_to_reviewer(self):
        self.client.force_login(self.learner);self.assertNotContains(self.client.get('/'),'Open review queue')
        self.client.force_login(self.reviewer);self.assertContains(self.client.get('/'),'Open review queue')
