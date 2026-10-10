import re

LESSON = {
    'title': 'Ordering at a Restaurant',
    'goal': 'Order food and a drink politely, then ask for the bill.',
    'grammar': 'Polite requests using "I would like" and "Can I have".',
    'target_words': ['menu', 'chicken', 'rice', 'soup', 'water', 'tea', 'bill', 'please'],
    'turn_limit': 5,
    'opening': 'Hello! Would you like a menu?',
    'menu': ['Chicken with rice', 'Soup', 'Water', 'Tea'],
}
BEGINNER_WORDS = set('a an the i you he she it we they me my your our is are am was were be been have has had do does did can could would will want like need order eat drink food yes no not and or but so with without for to from of in on at this that these those here there hello hi welcome thank thanks good great sure okay ok what how which some any one two three more anything else today ready take get bring enjoy much cost dollars please lets let us now goodbye'.split())
ALLOWED = BEGINNER_WORDS | set(LESSON['target_words'])
ALLOWED |= set('certainly right away coming meal small large hot cold sorry use say sentence polite request word words instead add after before correct restaurant waiter'.split())
TARGETS = {'microphone': 1000, 'transcription': 5000, 'ai_reply': 5000, 'playback': 1000, 'summary': 500, 'page_ready': 1500, 'system_total': 11000}


def words(text):
    text = text.lower().replace('’', "'")
    contractions = {"i'm": 'i am', "i'd": 'i would', "i'll": 'i will', "don't": 'do not', "can't": 'can not', "you're": 'you are', "it's": 'it is', "that's": 'that is', "we're": 'we are', "let's": 'let us'}
    for short, expanded in contractions.items():
        text = re.sub(r'\b' + re.escape(short) + r'\b', expanded, text)
    return re.findall(r"[a-z]+", text)


def outside_words(text):
    return sorted(set(words(text)) - ALLOWED)


def make_summary(turns):
    used = set(w for turn in turns for w in words(turn['learner']))
    return {
        'used': [w for w in LESSON['target_words'] if w in used],
        'unused': [w for w in LESSON['target_words'] if w not in used],
        'corrections': [{'original': t['learner'], **t['correction']} for t in turns if t['correction']],
    }
