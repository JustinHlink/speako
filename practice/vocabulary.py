from .lesson import words
from .models import SharedBeginnerWord

def allowed_words(lesson):
    lesson_words = set(lesson.words.values_list('word', flat=True))
    shared_words = set(SharedBeginnerWord.objects.values_list('word', flat=True))
    return lesson_words | shared_words

def outside_words(text, lesson):
    return sorted(set(words(text)) - allowed_words(lesson))

def lesson_is_configured(lesson):
    return (
        lesson.status == 'Published'
        and lesson.words.exists()
        and 5 <= lesson.turn_limit <= 30
    )