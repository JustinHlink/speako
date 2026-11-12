from django.db import migrations

WORDS = ['passport', 'visit', 'holiday', 'business', 'days', 'stay', 'bag', 'declare', 'please', 'purpose', 'trip', 'long', 'how', 'anything', 'nothing', 'ten']

def seed(apps, schema_editor):
    Lesson = apps.get_model('practice', 'Lesson')
    Word = apps.get_model('practice', 'LessonWord')
    lesson, _ = Lesson.objects.get_or_create(scenario='Passing Customs', defaults={
        'grammar_goal': 'Short answers using "I am here for", "I will stay", and "I have".',
        'turn_limit': 5, 'status': 'Published'})
    for word in WORDS:
        Word.objects.get_or_create(lesson=lesson, word=word)

class Migration(migrations.Migration):
    dependencies = [('practice', '0004_shared_beginner_function_words')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
