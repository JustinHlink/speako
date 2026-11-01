from django.test import TestCase

from .models import Lesson, LessonWord
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