"""Presentation and role instructions for the two fixed English scenarios."""
RESTAURANT = 'Ordering at a Restaurant'
CUSTOMS = 'Passing Customs'
CUSTOMS_WORDS = ['passport', 'visit', 'holiday', 'business', 'days', 'stay', 'bag', 'declare', 'please', 'purpose', 'trip', 'long', 'how', 'anything', 'nothing', 'ten']

def details(lesson):
    title = lesson.scenario if lesson else RESTAURANT
    if title == CUSTOMS:
        return {
            'goal': 'Answer simple questions about your visit and luggage.',
            'partner': 'The customs officer', 'speaker': 'OFFICER',
            'opening': 'Hello! Can I see your passport, please?',
            'context_title': 'Your visit',
            'context_items': ['Purpose: holiday or business', 'Length of stay: ten days', 'Luggage: one bag', 'Nothing to declare'],
            'role_instructions': 'Act as a customs officer. Ask simple questions about the passport, purpose of the visit, length of stay, and luggage. Follow the learner answers. Never act as a waiter or ask about food, drinks, orders, or bills. Do not request real passport numbers or other personal identifiers. This is language practice, not immigration advice.'
        }
    if title == RESTAURANT:
        return {
            'goal': 'Order food and a drink politely, then ask for the bill.',
            'partner': 'The restaurant waiter', 'speaker': 'WAITER',
            'opening': 'Hello! Welcome. What would you like today?',
            'context_title': "Today's menu", 'context_items': ['Chicken with rice', 'Soup', 'Water', 'Tea'],
            'role_instructions': 'Act as a restaurant waiter. For an accepted order, acknowledge it and ask one simple question about food, a drink, or the bill.'
        }
    return {'goal': lesson.grammar_goal if lesson else '', 'partner': 'Your conversation partner',
            'speaker': 'PARTNER', 'opening': 'Hello! Welcome. What would you like today?',
            'context_title': 'Practice focus', 'context_items': [],
            'role_instructions': 'Keep all questions relevant to the selected scenario.'}
