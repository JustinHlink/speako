import os
from django.core.management.base import BaseCommand, CommandError
from practice.models import User

# Demo accounts are made by an admin, never by self-registration (Interface Design, NFR 6).
DEMO_USERS = [
    ('learner1', 'Learner'),
    ('learner2', 'Learner'),
    ('curator1', 'Curator'),
    ('reviewer1', 'Reviewer'),
]


class Command(BaseCommand):
    help = 'Create or reset the demo accounts. The password is never stored in the repository.'

    def add_arguments(self, parser):
        parser.add_argument('--password', help='Password for every demo account (or set SPEAKO_DEMO_PASSWORD).')

    def handle(self, *args, **options):
        password = options['password'] or os.environ.get('SPEAKO_DEMO_PASSWORD', '')
        if len(password) < 8:
            raise CommandError('Give a demo password of at least 8 characters with --password or SPEAKO_DEMO_PASSWORD.')
        for username, role in DEMO_USERS:
            user, created = User.objects.get_or_create(username=username, defaults={'role': role})
            user.role = role
            user.set_password(password)
            user.save()
            self.stdout.write(f"{'Created' if created else 'Reset'} {username} ({role})")
