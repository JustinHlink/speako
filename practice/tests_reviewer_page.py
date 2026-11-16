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
        self.assertEqual(self.client.get('/api/flag/list/').status_code,401)
        self.assertEqual(self.client.post('/api/flag/review/',{'flag_id':self.flag.pk,'status':'Incorrect'},content_type='application/json').status_code,401)
        for role in ['Learner','Curator']:
            user=User.objects.create_user(username='denied-'+role,role=role);self.client.force_login(user)
            self.assertEqual(self.client.get('/review/').status_code,403)
            self.assertEqual(self.client.get('/api/flag/list/').status_code,403)
            self.assertEqual(self.client.post('/api/flag/review/',{'flag_id':self.flag.pk,'status':'Incorrect'},content_type='application/json').status_code,403)
        self.flag.refresh_from_db();self.assertEqual(self.flag.status,'Unresolved')
        self.client.force_login(self.reviewer)
        page=self.client.get('/review/');self.assertEqual(page.status_code,200)
        self.assertContains(page,'reviewer.js');self.assertIn('csrftoken',page.cookies)

    def test_non_learner_roles_cannot_submit_flags(self):
        unflagged_turn=Turn.objects.get(attempt=self.attempt,turn_number=1)
        for role in ['Reviewer','Curator']:
            user=User.objects.create_user(username='submit-denied-'+role,role=role);self.client.force_login(user)
            res=self.client.post('/api/flag/submit/',{'turn_id':unflagged_turn.pk},content_type='application/json')
            self.assertEqual(res.status_code,403)
        self.assertFalse(Flag.objects.filter(turn=unflagged_turn).exists())

    def test_register_cannot_escalate_to_reviewer_role(self):
        res=self.client.post('/api/auth/register/',{'username':'attempted-reviewer','password':'password123','role':'Reviewer'},content_type='application/json')
        self.assertEqual(res.status_code,201)
        created_user=User.objects.get(username='attempted-reviewer')
        self.assertEqual(created_user.role,'Learner')
        self.assertEqual(self.client.get('/review/').status_code,403)
        self.assertEqual(self.client.get('/api/flag/list/').status_code,403)

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
        self.assertNotContains(self.client.get('/'),'Open review queue')
        self.client.force_login(self.learner);self.assertNotContains(self.client.get('/'),'Open review queue')
        curator=User.objects.create_user(username='home-curator',role='Curator')
        self.client.force_login(curator);self.assertNotContains(self.client.get('/'),'Open review queue')
        self.client.force_login(self.reviewer);self.assertContains(self.client.get('/'),'Open review queue')

    def test_learner_flag_to_reviewer_decision_end_to_end(self):
        turn=Turn.objects.create(attempt=self.attempt,turn_number=3,learner_text='Yes please.',ai_reply='Thank you.',pending_id='queue-end-to-end')
        self.client.force_login(self.learner)
        created=self.client.post('/api/flag/submit/',{'turn_id':turn.pk},content_type='application/json')
        self.assertEqual(created.status_code,201)
        flag_id=created.json()['flag']['id']
        self.client.force_login(self.reviewer)
        items=self.client.get('/api/flag/list/').json()['flags']
        self.assertIn(flag_id,[item['id'] for item in items])
        result=self.client.post('/api/flag/review/',{'flag_id':flag_id,'status':'Acceptable'},content_type='application/json')
        self.assertEqual(result.status_code,200)
        self.assertNotIn(flag_id,[item['id'] for item in self.client.get('/api/flag/list/').json()['flags']])
        self.client.force_login(self.learner)
        self.assertEqual(self.client.post('/api/flag/submit/',{'turn_id':turn.pk},content_type='application/json').status_code,409)
        self.attempt.refresh_from_db();self.assertEqual(self.attempt.status,'In progress')

    def test_complete_attempt_context_includes_later_turns(self):
        Turn.objects.create(attempt=self.attempt,turn_number=3,learner_text='Thank you.',ai_reply='Goodbye.',pending_id='after-flag')
        self.client.force_login(self.reviewer)
        item=self.client.get('/api/flag/list/').json()['flags'][0]
        self.assertEqual(item['attempt_id'],str(self.attempt.pk))
        self.assertEqual([turn['turn_number'] for turn in item['turns']],[1,2,3])
        self.assertEqual([turn['turn_number'] for turn in item['turns'] if turn['is_flagged']],[2])
        self.assertEqual(item['turns'][1]['correction']['example'],'I like water.')

    def test_seed_script_preserves_existing_flags_progress_and_reviews(self):
        import runpy
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        previous_attempts=set(LessonAttempt.objects.values_list('pk',flat=True))
        with redirect_stdout(StringIO()):
            runpy.run_path(str(Path(__file__).resolve().parent.parent/'seed_flags.py'))
        self.flag.refresh_from_db()
        self.assertEqual(self.flag.status,'Unresolved')
        fixtures=LessonAttempt.objects.filter(learner__username__startswith='review-fixture-')
        self.assertEqual(fixtures.count(),6)
        self.assertTrue(all(x.status=='Exited' for x in fixtures))
        fixture_flag=Flag.objects.filter(turn__attempt__in=fixtures).first()
        fixture_flag.status='Acceptable';fixture_flag.reviewer=self.reviewer;fixture_flag.save()
        counts=(LessonAttempt.objects.count(),Flag.objects.count(),Turn.objects.count())
        with redirect_stdout(StringIO()):
            runpy.run_path(str(Path(__file__).resolve().parent.parent/'seed_flags.py'))
        self.assertEqual((LessonAttempt.objects.count(),Flag.objects.count(),Turn.objects.count()),counts)
        fixture_flag.refresh_from_db();self.assertEqual(fixture_flag.status,'Acceptable')
        self.assertTrue(previous_attempts.issubset(set(LessonAttempt.objects.values_list('pk',flat=True))))
