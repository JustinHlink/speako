import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speako.settings')
django.setup()

from practice.models import User, Lesson, LessonAttempt, Turn, Flag, Correction

learner1 = User.objects.get(username='learner1')
learner2 = User.objects.get(username='learner2')
lesson = Lesson.objects.first()

# Clear existing unresolved test flags and their completed/exited test attempts
Flag.objects.filter(status='Unresolved').delete()

test_cases = [
    {
        'learner': learner1,
        'status': 'Completed',
        'history': [
            ('Hello, good evening.', 'Good evening! Welcome to our restaurant. What would you like to drink?')
        ],
        'learner_text': 'I wants a cup of hot green tea please.',
        'ai_reply': 'Sure, one hot green tea. Would you like anything to eat with that?',
        'correction': ("Use 'want' instead of 'wants' with the pronoun 'I'.", 'I want a cup of hot green tea please.'),
        'after': [
            ('I would like the chicken salad.', 'Great choice! Anything else for you?'),
            ('No, that is all. Thank you.', 'Your order will be ready shortly!')
        ]
    },
    {
        'learner': learner1,
        'status': 'Exited',
        'history': [
            ('Can I see the menu please?', 'Here is the menu. Take your time.')
        ],
        'learner_text': 'How much is the beef steak?',
        'ai_reply': 'The steak is 42 credits in the Galactic Federation currency. Please prepare your teleportation device for payment.',
        'correction': None,
        'after': [
            ('Wait, what do you mean by Galactic credits?', 'Apologies, the steak is $24.')
        ]
    },
    {
        'learner': learner2,
        'status': 'Completed',
        'history': [
            ('Could I see the menu?', "Of course, here is the menu. Today's special is grilled salmon."),
            ('Is the salmon fresh?', 'Yes, delivered fresh this morning.')
        ],
        'learner_text': 'Actually, to be completely honest with you, I am extremely hungry because I have been walking around the city sightseeing all afternoon without having lunch, so could you please recommend some of your most popular dishes and tell me if they contain any peanuts because I am quite allergic to them?',
        'ai_reply': 'We would be delighted to recommend our specialty roasted chicken with seasonal vegetables and mashed potatoes, which is completely peanut-free. We also have a lovely fresh garden salad with olive oil dressing, and our kitchen takes allergies very seriously so we will ensure extra care is taken with your order.',
        'correction': None,
        'after': [
            ('I will take the roasted chicken then.', 'Wonderful, one peanut-free roasted chicken coming right up!'),
            ('Could I also get a glass of water?', 'Certainly, I will bring a glass of water right away.')
        ]
    },
    {
        'learner': learner2,
        'status': 'Exited',
        'history': [],
        'learner_text': 'Water.',
        'ai_reply': 'Certainly, still or sparkling water?',
        'correction': ("Make requests more polite using 'Could I have...?'", 'Could I have some water, please?'),
        'after': [
            ('Could I have still water, please?', 'Of course, one still water for you.')
        ]
    },
    {
        'learner': learner1,
        'status': 'Completed',
        'history': [
            ('Excuse me, waiter.', 'Yes, how may I help you?')
        ],
        'learner_text': "Could you please explain what the soup of the day is, because the menu only says chef's special soup and does not describe whether it is creamy mushroom soup or tomato basil soup or something else entirely?",
        'ai_reply': "Today's soup is creamy wild mushroom soup served with toasted garlic bread.",
        'correction': None,
        'after': [
            ('Sounds delicious, I will have a bowl of soup.', 'One bowl of mushroom soup, coming right up!')
        ]
    },
    {
        'learner': learner2,
        'status': 'Completed',
        'history': [
            ('Everything was delicious, thank you.', 'I am glad you enjoyed the meal! Would you like the bill?')
        ],
        'learner_text': 'We would like to pay by credit card, but we need two separate receipts for company expense reimbursement purposes.',
        'ai_reply': 'No problem at all! I can split the bill equally or by item, whichever you prefer.',
        'correction': None,
        'after': [
            ('Please split it equally.', 'Here are your two receipts. Have a wonderful evening!')
        ]
    }
]

created_flags = []
for case in test_cases:
    attempt = LessonAttempt.objects.create(
        learner=case['learner'],
        lesson=lesson,
        status=case['status'],
        opening_line='Welcome to our restaurant! How can I help you today?'
    )
    turn_num = 1
    for h_learner, h_ai in case['history']:
        Turn.objects.create(
            attempt=attempt,
            turn_number=turn_num,
            learner_text=h_learner,
            ai_reply=h_ai,
            pending_id=str(uuid.uuid4())
        )
        turn_num += 1
    
    flag_turn = Turn.objects.create(
        attempt=attempt,
        turn_number=turn_num,
        learner_text=case['learner_text'],
        ai_reply=case['ai_reply'],
        pending_id=str(uuid.uuid4())
    )
    turn_num += 1
    if case['correction']:
        expl, ex = case['correction']
        Correction.objects.create(turn=flag_turn, explanation=expl, corrected_example=ex)
    
    for a_learner, a_ai in case.get('after', []):
        Turn.objects.create(
            attempt=attempt,
            turn_number=turn_num,
            learner_text=a_learner,
            ai_reply=a_ai,
            pending_id=str(uuid.uuid4())
        )
        turn_num += 1

    flag = Flag.objects.create(turn=flag_turn, status='Unresolved')
    created_flags.append(flag.id)

print(f'Successfully created {len(created_flags)} test flags: {created_flags}')
