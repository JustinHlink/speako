import os
import uuid
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speako.settings')
django.setup()

from practice.models import (
    User, Lesson, LessonWord, LessonAttempt, Turn, Correction, LessonSummary, Flag
)

# 1. Ensure demo users exist
reviewer1, _ = User.objects.get_or_create(username='reviewer1', defaults={'role': 'Reviewer'})
if not reviewer1.has_usable_password():
    reviewer1.set_password('speako1234')
    reviewer1.save()
learner1, _ = User.objects.get_or_create(username='learner1', defaults={'role': 'Learner'})
if not learner1.has_usable_password():
    learner1.set_password('speako1234')
    learner1.save()

learner2, _ = User.objects.get_or_create(username='learner2', defaults={'role': 'Learner'})
if not learner2.has_usable_password():
    learner2.set_password('speako1234')
    learner2.save()

# 2. Ensure all 5 MVP Published Lessons from Sprint 2 Design Doc exist on the Learning Map
lessons_spec = [
    {
        'scenario': 'Ordering at a Restaurant',
        'grammar_goal': 'Use polite requests like "I would like..." and "Could I have...?" to order food, drinks, and ask for the bill.',
        'turn_limit': 5,
        'words': ['menu', 'water', 'tea', 'chicken', 'rice', 'soup', 'bill', 'please']
    },
    {
        'scenario': 'Passing Customs',
        'grammar_goal': 'Give clear, short factual answers about your passport, purpose of visit, length of stay, and luggage.',
        'turn_limit': 5,
        'words': ['passport', 'holiday', 'stay', 'days', 'bag', 'declare', 'hotel', 'visit']
    },
    {
        'scenario': 'Checking into a Hotel',
        'grammar_goal': 'Ask polite questions about room reservation, breakfast hours, and key cards.',
        'turn_limit': 5,
        'words': ['room', 'name', 'night', 'breakfast', 'key', 'morning', 'thank', 'help']
    },
    {
        'scenario': 'Asking for Directions',
        'grammar_goal': 'Ask where places are and confirm simple directions using "Where is...?" and "How far is...?".',
        'turn_limit': 5,
        'words': ['station', 'street', 'left', 'right', 'walk', 'near', 'far', 'map']
    },
    {
        'scenario': 'Greetings and Introductions',
        'grammar_goal': 'Introduce yourself, say where you are from, and greet a new friend politely.',
        'turn_limit': 5,
        'words': ['hello', 'name', 'meet', 'from', 'student', 'work', 'nice', 'goodbye']
    }
]

lessons = {}
Lesson.objects.filter(scenario='Hotel Check-in').delete()
for spec in lessons_spec:
    lesson, _ = Lesson.objects.update_or_create(
        scenario=spec['scenario'],
        defaults={
            'grammar_goal': spec['grammar_goal'],
            'turn_limit': spec['turn_limit'],
            'status': 'Published'
        }
    )
    for w in spec['words']:
        LessonWord.objects.get_or_create(lesson=lesson, word=w)
    lessons[spec['scenario']] = lesson

# 3. Seed Learning Map progress states for learner1:
#    - Lesson 1 (Ordering at a Restaurant): Completed (with Summary + Corrections)
#    - Lesson 2 (Passing Customs): In progress (with 2 saved turns)
#    - Lesson 3 (Hotel Check-in): Completed (with Summary, no mistakes)
#    - Lesson 4 (Asking for Directions): Not started (no attempts)

LessonAttempt.objects.filter(learner=learner1).delete()

# Lesson 1: Completed with summary & corrections
att1 = LessonAttempt.objects.create(
    learner=learner1,
    lesson=lessons['Ordering at a Restaurant'],
    status='Completed',
    opening_line='Hello! Welcome to our restaurant. What would you like today?',
    ended_at=timezone.now()
)
t1 = Turn.objects.create(
    attempt=att1, turn_number=1,
    learner_text='Could I see the menu please?',
    ai_reply='Of course! Here is the menu. Would you like water or tea?',
    pending_id=str(uuid.uuid4())
)
t2 = Turn.objects.create(
    attempt=att1, turn_number=2,
    learner_text='I wants a cup of hot tea please.',
    ai_reply='Sure, one hot tea. What would you like to eat?',
    pending_id=str(uuid.uuid4())
)
Correction.objects.create(
    turn=t2,
    explanation="Use 'want' or 'would like' with 'I' instead of 'wants'.",
    corrected_example='I would like a cup of hot tea, please.'
)
t3 = Turn.objects.create(
    attempt=att1, turn_number=3,
    learner_text='I would like chicken and rice.',
    ai_reply='Great choice! The chicken with rice costs 500 gold coins. Would you like soup as well?',
    pending_id=str(uuid.uuid4())
)
Flag.objects.create(
    turn=t3,
    status='Incorrect',
    reviewer=reviewer1,
    reviewed_at=timezone.now()
)
Turn.objects.create(
    attempt=att1, turn_number=4,
    learner_text='No soup, just water please.',
    ai_reply='Certainly, I will bring your water, tea, and chicken with rice.',
    pending_id=str(uuid.uuid4())
)
Turn.objects.create(
    attempt=att1, turn_number=5,
    learner_text='Could I have the bill please?',
    ai_reply='Here is your bill. Thank you for dining with us!',
    pending_id=str(uuid.uuid4())
)
LessonSummary.objects.create(
    attempt=att1,
    words_used=['menu', 'tea', 'chicken', 'rice', 'water', 'bill', 'please'],
    words_not_used=['soup']
)

# Lesson 2: In progress (2 / 5 turns completed)
att2 = LessonAttempt.objects.create(
    learner=learner1,
    lesson=lessons['Passing Customs'],
    status='In progress',
    opening_line='Good morning. May I see your passport, please?'
)
Turn.objects.create(
    attempt=att2, turn_number=1,
    learner_text='Here is my passport.',
    ai_reply='Thank you. Are you here for a holiday or business visit?',
    pending_id=str(uuid.uuid4())
)
Turn.objects.create(
    attempt=att2, turn_number=2,
    learner_text='I am here for a holiday.',
    ai_reply='How many days will you stay, and where is your hotel?',
    pending_id=str(uuid.uuid4())
)

# Lesson 3: Exited early (which maps to "In progress" on the Learning Map per DR-03)
att3 = LessonAttempt.objects.create(
    learner=learner1,
    lesson=lessons['Checking into a Hotel'],
    status='Exited',
    opening_line='Welcome to the Grand Hotel! Do you have a room reservation?',
    ended_at=timezone.now()
)
Turn.objects.create(
    attempt=att3, turn_number=1,
    learner_text='Yes, I have a room for two nights under my name.',
    ai_reply='Thank you! Here is your key. Breakfast starts at seven in the morning.',
    pending_id=str(uuid.uuid4())
)

# Lesson 4 (Asking for Directions) & Lesson 5 (Greetings and Introductions): No attempts -> "Not started"

print('Successfully seeded all 5 MVP Published lessons and Learning Map test progress for learner1:')
print('  1. Ordering at a Restaurant    -> Completed (with saved summary & correction)')
print('  2. Passing Customs             -> In progress (active attempt at Turn 2/5)')
print('  3. Checking into a Hotel       -> In progress (exited halfway attempt, DR-03)')
print('  4. Asking for Directions       -> Not started')
print('  5. Greetings and Introductions -> Not started')
