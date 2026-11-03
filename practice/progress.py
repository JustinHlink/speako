from .models import LessonAttempt

# Learning-map status is computed from attempts, never stored (DR-03, ST-03).
COMPLETED, IN_PROGRESS, NOT_STARTED = 'Completed', 'In progress', 'Not started'


def map_statuses(learner, lessons):
    """Return {lesson_id: status} for one learner. Only this learner's attempts are read (US-16 AC3, NFR 1)."""
    attempts = LessonAttempt.objects.filter(learner=learner, lesson__in=lessons)
    started = set(attempts.values_list('lesson_id', flat=True))
    completed = set(attempts.filter(status=COMPLETED).values_list('lesson_id', flat=True))
    statuses = {}
    for lesson in lessons:
        if lesson.pk in completed:
            statuses[lesson.pk] = COMPLETED  # a later exited retake never hides a completion (US-16 AC1)
        elif lesson.pk in started:
            statuses[lesson.pk] = IN_PROGRESS  # In progress or Exited attempt (US-16 AC2)
        else:
            statuses[lesson.pk] = NOT_STARTED
    return statuses


def map_status(learner, lesson):
    return map_statuses(learner, [lesson])[lesson.pk]


def latest_completed_attempt(learner, lesson):
    """The attempt whose summary the learning map reopens (US-18 AC4).

    Attempts without ended_at are skipped, since some databases sort NULL first.
    """
    return (LessonAttempt.objects.filter(learner=learner, lesson=lesson, status=COMPLETED,
                                         ended_at__isnull=False)
            .order_by('-ended_at').first())
