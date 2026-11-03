from django.db import migrations


def add_basic_verb(apps, schema_editor):
    # A shared beginner verb, distinct from the lesson's target vocabulary.
    apps.get_model('practice', 'SharedBeginnerWord').objects.get_or_create(word='see')


class Migration(migrations.Migration):
    dependencies = [('practice', '0002_seed_lesson_vocabulary')]
    operations = [migrations.RunPython(add_basic_verb, migrations.RunPython.noop)]
