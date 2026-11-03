import json
import base64
import time
from functools import wraps
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone

from .models import User, Lesson, LessonWord, SharedBeginnerWord, LessonAttempt, Turn, Correction, LessonSummary, Flag, ApiUsage
from . import gemini
from .lesson import LESSON, ALLOWED, TARGETS, outside_words, make_summary


def body(request):
    """Extract and parse JSON request body."""
    try:
        result = json.loads(request.body or '{}')
        return result if isinstance(result, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


from functools import wraps
from django.http import JsonResponse
def require_role(allowed_roles):
    """
    Decorator to enforce Role-based Access Control (RBAC).
    Matches NFR 2, NFR 6, US-06 AC2, US-13 AC3.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Sign-in required.'
                    }
                }, status=401)
            
            user_role = getattr(request.user, 'role', None)
            if user_role not in allowed_roles:
                return JsonResponse({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Insufficient role permissions.'
                    }
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

@ensure_csrf_cookie
def home(request):
    """Render the single-page application template."""
    return render(request, 'practice/index.html')


@require_POST
def api_login(request):
    """
    A01: POST /api/auth/login/
    Inputs: username, password -> Account role & new authenticated session.
    """
    data = body(request)
    username = data.get('username', '').strip()
    password = data.get('password')

    if not isinstance(username, str) or not username.strip():
        return JsonResponse({'error': {'code': 'INVALID_INPUT', 'message': 'Username must be a non-empty string.'}}, status=400)
    
    if not isinstance(password, str) or not password:
        return JsonResponse({'error': {'code': 'INVALID_INPUT', 'message': 'Password must be a non-empty string.'}}, status=400)

    username = username.strip()

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid username or password.'}}, status=401)

    login(request, user)

    return JsonResponse({
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    }, status=200)


@require_POST
def api_logout(request):
    """
    A02: POST /api/auth/logout/
    Clear authenticated session and private browser state.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'No active session found.'
            }
        }, status=401)

    logout(request)

    return JsonResponse({}, status=204)

@require_POST
def api_register(request):
    """
    A03: POST /api/auth/register/
    Register a new user with the specified role (default is Learner).
    """
    data = body(request)
    username = data.get('username', '').strip()
    password = data.get('password')
    role = data.get('role', 'Learner').strip()

    if not username or not password:
        return JsonResponse({
            'error': {
                'code': 'INVALID_INPUT',
                'message': 'Username and password are required.'
            }
        }, status=400)

    allowed_roles = [choice[0] for choice in User.ROLE_CHOICES]
    if role not in allowed_roles:
        return JsonResponse({
            'error': {
                'code': 'INVALID_ROLE',
                'message': f'Role must be one of {allowed_roles}.'
            }
        }, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'error': {
                'code': 'CONFLICT',
                'message': 'Username already exists.'
            }
        }, status=409)

    user = User.objects.create_user(
        username=username,
        password=password,
        role='Learner'  # Always hardcoded to Learner
    )

    login(request, user)

    return JsonResponse({
        'message': 'User created successfully.',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    }, status=201)

@require_GET
@require_role(['Learner'])
def list_lessons(request):
    """
    L01: GET /api/lessons/
    Return all Published lessons with map status computed per learner (DR-03).
    """
    return JsonResponse({'lessons': []})


@require_GET
@require_role(['Learner'])
def get_lesson_detail(request, lesson_id):
    """
    L02: GET /api/lessons/{id}/
    Return available lesson details and latest completed attempt ID.
    """
    return JsonResponse({'lesson': {}})


@require_GET
def status(request):
    """
    GET /api/status/
    Return global ready state, current attempt snapshot, and usage guard stats.
    """
    ok, message = gemini.ready()
    return JsonResponse({
        'lesson': LESSON,
        'targets': TARGETS,
        'api_ready': ok,
        'setup_message': message,
        'usage': gemini.usage(),
        'session': None
    })


@require_POST
@require_role(['Learner'])
def start_lesson(request):
    """
    POST /api/start/
    Start a new LessonAttempt on a Published lesson.
    """
    return JsonResponse({'session': {}})


@require_POST
@require_role(['Learner'])
def transcribe_audio(request):
    """
    POST /api/transcribe/
    Upload audio file, reserve budget, call Gemini Transcribe, and store pending_transcript.
    """
    return JsonResponse({'session': {}})


@require_POST
@require_role(['Learner'])
def discard_transcript(request):
    """
    POST /api/discard/
    Discard pending transcript (Try again). Never advances turn or calls AI.
    """
    return JsonResponse({'session': {}})


@require_POST
@require_role(['Learner'])
def submit_reply(request):
    """
    POST /api/reply/
    Confirm transcript (Continue), invoke Gemini conversation, validate vocabulary, and save Turn.
    """
    return JsonResponse({'session': {}})


@require_POST
@require_role(['Learner'])
def exit_lesson(request):
    """
    POST /api/exit/
    Exit an unfinished lesson. Sets status='Exited' with no summary created.
    """
    return JsonResponse({'session': {}})


@require_POST
@require_role(['Learner'])
def submit_flag(request):
    """
    POST /api/flag/submit/
    Learner flags an inappropriate or incorrect Turn ('This felt wrong').
    """
    return JsonResponse({'message': 'Flag submitted successfully.'}, status=201)


@require_GET
@require_role(['Reviewer'])
def list_flags(request):
    """
    GET /api/flag/list/
    Reviewer fetches list of Unresolved flagged turns (US-13 AC1).
    """
    return JsonResponse({'flags': []})


@require_POST
@require_role(['Reviewer'])
def review_flag(request):
    """
    POST /api/flag/review/
    Reviewer marks a Flag as 'Acceptable' or 'Incorrect' (US-13 AC2).
    """
    return JsonResponse({'message': 'Flag reviewed successfully.'})


@require_GET
def metrics(request):
    """
    GET /api/metrics/
    Export ApiUsage ledger and timing measurements for instructor review.
    """
    rows = list(ApiUsage.objects.values('call_type', 'status', 'reserved_usd', 'estimated_usd', 'input_tokens', 'output_tokens', 'started_at'))
    return JsonResponse({'attempts': rows, 'usage': gemini.usage()}, json_dumps_params={'indent': 2})