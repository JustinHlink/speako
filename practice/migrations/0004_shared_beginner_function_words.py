from django.db import migrations


def add_basic_verb(apps, schema_editor):
    # A shared beginner verb, distinct from the lesson's target vocabulary.
    shared = apps.get_model('practice', 'SharedBeginnerWord')
    for word in 'see all also just very well about if then when where why who how which any other another both each only again still already yet soon please certainly really too much little more less first next last today now here there your our their its'.split():
        shared.objects.get_or_create(word=word)


class Migration(migrations.Migration):
    dependencies = [('practice', '0003_shared_beginner_see')]
    operations = [migrations.RunPython(add_basic_verb, migrations.RunPython.noop)]
