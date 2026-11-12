import json
from unittest.mock import patch
from django.test import TestCase, Client
from .models import User, Lesson, LessonAttempt, Turn, Flag, LessonSummary, Correction
from . import scenarios, vocabulary, views


class CustomsFlowTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='customs-learner')
        self.client.force_login(self.user)
        self.customs=Lesson.objects.get(scenario=scenarios.CUSTOMS)
        self.restaurant=Lesson.objects.get(scenario=scenarios.RESTAURANT)

    def test_published_lesson_details_and_opening_are_independent(self):
        lessons=self.client.get('/api/lessons/').json()['lessons']
        self.assertIn(self.customs.pk,[item['id'] for item in lessons])
        detail=self.client.get(f'/api/lessons/{self.customs.pk}/').json()['lesson']
        self.assertEqual(detail['presentation']['speaker'],'OFFICER')
        self.assertIn('passport',detail['target_words'])
        self.assertNotIn('menu',detail['target_words'])
        self.assertFalse(vocabulary.outside_words(detail['presentation']['opening'],self.customs))
        result=self.client.post('/api/start/',{'lesson_id':self.customs.pk},content_type='application/json')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['attempt']['opening'],detail['presentation']['opening'])
        prompt=views.reply_instructions(self.customs,1)
        self.assertIn('Act as a customs officer',prompt)
        self.assertNotIn('For an accepted order',prompt)
        self.assertIn('Act as a restaurant waiter',views.reply_instructions(self.restaurant,1))

    @patch('practice.providers.reply')
    def test_five_confirmed_customs_turns_save_summary_without_completing_restaurant(self,reply):
        reply.return_value={'reply':'Thank you. How long will you stay?', 'correction_explanation':'','corrected_example':'','off_topic':False}
        started=self.client.post('/api/start/',{'lesson_id':self.customs.pk},content_type='application/json').json()
        attempt=LessonAttempt.objects.get(pk=started['attempt']['attempt_id'])
        for i,text in enumerate(['Here is my passport.','I am here for a holiday.','I will stay ten days.','I have one bag.','I have nothing to declare.'],1):
            attempt.pending_id=f'customs-{i}';attempt.pending_transcript=text;attempt.save()
            response=self.client.post('/api/reply/',{'attempt_id':str(attempt.pk),'pending_id':attempt.pending_id},content_type='application/json')
            self.assertEqual(response.status_code,200,response.content)
        attempt.refresh_from_db();self.assertEqual(attempt.status,'Completed')
        self.assertEqual(attempt.turns.count(),5)
        self.assertIn('passport',attempt.summary.words_used)
        self.assertNotIn('menu',attempt.summary.words_used+attempt.summary.words_not_used)
        statuses={x['id']:x['status_on_map'] for x in self.client.get('/api/lessons/').json()['lessons']}
        self.assertEqual(statuses[self.restaurant.pk],'Not started')
        self.assertEqual(statuses[self.customs.pk],'Completed')
        other=User.objects.create_user(username='other-customs')
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/api/attempts/{attempt.pk}/summary/').status_code,404)

    @patch('practice.providers.reply')
    def test_off_topic_is_redirected_without_false_correction(self,reply):
        reply.return_value={'reply':'Can I see your passport, please?', 'correction_explanation':'','corrected_example':'','off_topic':True}
        attempt=LessonAttempt.objects.create(learner=self.user,lesson=self.customs,opening_line='Hello!',pending_id='off-topic-customs',pending_transcript='I would like soup.')
        result=self.client.post('/api/reply/',{'attempt_id':str(attempt.pk),'pending_id':attempt.pending_id},content_type='application/json')
        self.assertEqual(result.status_code,200)
        self.assertFalse(Correction.objects.filter(turn__attempt=attempt).exists())
        self.assertIn('passport',attempt.turns.get().ai_reply)

    def test_customs_draft_and_unauthorized_start_are_rejected(self):
        self.customs.status='Draft';self.customs.save()
        self.assertEqual(self.client.post('/api/start/',{'lesson_id':self.customs.pk},content_type='application/json').status_code,409)
        self.client.logout()
        self.assertEqual(self.client.post('/api/start/',{'lesson_id':self.customs.pk},content_type='application/json').status_code,401)


class FlagBrowserContractTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='flag-page-owner')
        self.client.force_login(self.user)
        self.attempt=LessonAttempt.objects.create(learner=self.user,lesson=Lesson.objects.get(scenario=scenarios.CUSTOMS),opening_line='Hello!')
        self.turn=Turn.objects.create(attempt=self.attempt,turn_number=1,learner_text='My passport.',ai_reply='Thank you.',pending_id='flag-contract')

    def test_turn_ids_and_flag_state_survive_reload_without_changing_attempt(self):
        initial=self.client.get('/api/status/').json()['attempt']['turns'][0]
        self.assertEqual(initial['id'],self.turn.pk);self.assertFalse(initial['flagged'])
        response=self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json')
        self.assertEqual(response.status_code,201)
        self.assertTrue(self.client.get('/api/status/').json()['attempt']['turns'][0]['flagged'])
        self.assertEqual(self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json').status_code,409)
        self.assertEqual(Flag.objects.count(),1)
        self.attempt.refresh_from_db();self.assertEqual(self.attempt.status,'In progress')
        self.assertEqual(self.attempt.turns.count(),1);self.assertFalse(LessonSummary.objects.exists())

    def test_only_owner_can_flag_and_other_roles_are_denied(self):
        for role in ['Learner','Reviewer','Curator']:
            user=User.objects.create_user(username='flag-'+role,role=role);self.client.force_login(user)
            response=self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json')
            self.assertEqual(response.status_code,404 if role=='Learner' else 403)
        self.client.logout()
        self.assertEqual(self.client.post('/api/flag/submit/',{'turn_id':self.turn.pk},content_type='application/json').status_code,401)
        self.assertFalse(Flag.objects.exists())
