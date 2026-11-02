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
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return JsonResponse({'error': {'code': 'INVALID_INPUT', 'message': 'Username and password required.'}}, status=400)
    
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid credentials.'}}, status=401)
    
    login(request, user)
    return JsonResponse({
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })


@require_POST
def api_logout(request):
    """
    A02: POST /api/auth/logout/
    Clear authenticated session and private browser state.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': {'code': 'UNAUTHORIZED', 'message': 'No active session.'}}, status=401)
    
    logout(request)
    return JsonResponse({}, status=204)

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
    data = json.loads(request.body)
    turn_id = data.get('turn_id')
    if not turn_id:
        return JsonResponse({'error': {'code': 'INVALID_INPUT', 'message': 'turn_id is required.'}}, status=400)

    try:
        turn = Turn.objects.get(pk=turn_id, attempt__learner=request.user)
    except Turn.DoesNotExist:
        return JsonResponse({'error': {'code': 'NOT_FOUND', 'message': 'Turn not found or access denied.'}}, status=404)

    if hasattr(turn, 'flag'):
        return JsonResponse({'error': {'code': 'CONFLICT', 'message': 'This turn has already been flagged.'}}, status=409)

    flag = Flag.objects.create(
        turn=turn,
        status='Unresolved'
    )

    return JsonResponse({
        'message': 'Flag submitted successfully.',
        'flag': {
            'id': flag.id,
            'turn_id': turn.id,
            'status': flag.status,
            'flagged_at': flag.flagged_at.isoformat()
        }
    }, status=201)


@require_GET
@require_role(['Reviewer'])
def list_flags(request):
    """
    GET /api/flag/list/
    Reviewer fetches list of Unresolved flagged turns (US-13 AC1).
    """
    unresolved_flags = Flag.objects.filter(status='Unresolved').select_related('turn', 'turn__attempt__lesson')
    falg_list = []
    for f in unresolved_flags:
        falg_list.append({
            'id': f.id,
            'turn_id': f.turn.id,
            'scenario': f.turn.attempt.lesson.scenario,
            'learner_text': f.turn.learner_text,
            'ai_reply': f.turn.ai_reply,
            'flagged_at': f.flagged_at,
        })
    return JsonResponse({'flags': falg_list})


@require_POST
@require_role(['Reviewer'])
def review_flag(request):
    """
    POST /api/flag/review/
    Reviewer marks a Flag as 'Acceptable' or 'Incorrect' (US-13 AC2).
    """
    data = body(request)
    flag_id = data.get('flag_id')
    new_status = data.get('status')

    if new_status not in ['Acceptable', 'Incorrect']:
        return JsonResponse({'error': {'code': 'INVALID_INPUT', 'message': 'Status must be Acceptable or Incorrect.'}}, status=400)

    try:
        flag = Flag.objects.get(pk=flag_id)
    except Flag.DoesNotExist:
        return JsonResponse({'error': {'code': 'NOT_FOUND', 'message': 'Flag record not found.'}}, status=404)

    flag.status = new_status
    flag.reviewer = request.user
    flag.reviewed_at = timezone.now()
    flag.save()

    return JsonResponse({
        'message': 'Flag reviewed successfully.',
        'flag': {
            'id': flag.id,
            'status': flag.status,
            'reviewer': request.user.username,
            'reviewed_at': flag.reviewed_at.isoformat()
        }
    })


@require_GET
def metrics(request):
    """
    GET /api/metrics/
    Export ApiUsage ledger and timing measurements for instructor review.
    """
    rows = list(ApiUsage.objects.values('call_type', 'status', 'reserved_usd', 'estimated_usd', 'input_tokens', 'output_tokens', 'started_at'))
    return JsonResponse({'attempts': rows, 'usage': gemini.usage()}, json_dumps_params={'indent': 2})