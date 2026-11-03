import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    ROLE_CHOICES = [
        ('Learner', 'Learner'),
        ('Curator', 'Curator'),
        ('Reviewer', 'Reviewer'),
    ]
    # UQ: username
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Learner')

    def __str__(self):
        return f"{self.username} ({self.role})"


class Lesson(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    ]
    scenario = models.CharField(max_length=100)
    grammar_goal = models.TextField()
    turn_limit = models.IntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(30)],
        default=5
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')

    def __str__(self):
        return f"{self.scenario} [{self.status}]"


class LessonWord(models.Model):
    # FK: lesson_id -> Lesson
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='words')
    word = models.CharField(max_length=50)

    class Meta:
        # UQ: (lesson_id, word)
        unique_together = ('lesson', 'word')

    def save(self, *args, **kwargs):
        self.word = self.word.lower().strip()
        super().save(*args, **kwargs)


class SharedBeginnerWord(models.Model):
    word = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        self.word = self.word.lower().strip()
        super().save(*args, **kwargs)


class LessonAttempt(models.Model):
    STATUS_CHOICES = [
        ('In progress', 'In progress'),
        ('Completed', 'Completed'),
        ('Exited', 'Exited'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # FK: learner_id -> User
    learner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    # FK: lesson_id -> Lesson
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='In progress')
    opening_line = models.TextField()
    
    pending_transcript = models.TextField(blank=True, default='')  # empty if none
    pending_id = models.CharField(max_length=64, blank=True, default='')  # empty if none
    busy = models.BooleanField(default=False)  # a request is running
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)  # empty while In progress

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['learner'],
                condition=models.Q(status='In progress'),
                name='unique_in_progress_attempt_per_learner'
            )
        ]


class Turn(models.Model):
    # FK: attempt_id -> LessonAttempt
    attempt = models.ForeignKey(LessonAttempt, on_delete=models.CASCADE, related_name='turns')
    turn_number = models.IntegerField()  # 1 to turn_limit
    learner_text = models.TextField()  # confirmed transcript
    ai_reply = models.TextField()      # passed the word-list check
    
    # UQ: pending_id (the transcript it accepted)
    pending_id = models.CharField(max_length=64, unique=True)

    class Meta:
        unique_together = ('attempt', 'turn_number')


class Correction(models.Model):
    # FK, UQ: turn_id -> Turn
    turn = models.OneToOneField(Turn, on_delete=models.CASCADE, related_name='correction')
    explanation = models.TextField()  # one sentence
    corrected_example = models.TextField()


class LessonSummary(models.Model):
    # FK, UQ: attempt_id -> LessonAttempt
    attempt = models.OneToOneField(LessonAttempt, on_delete=models.CASCADE, related_name='summary')
    words_used = models.JSONField(default=list)
    words_not_used = models.JSONField(default=list)


class Flag(models.Model):
    STATUS_CHOICES = [
        ('Unresolved', 'Unresolved'),
        ('Acceptable', 'Acceptable'),
        ('Incorrect', 'Incorrect'),
    ]
    # FK, UQ: turn_id -> Turn (OneToOneField)
    turn = models.OneToOneField(Turn, on_delete=models.CASCADE, related_name='flag')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unresolved')
    
    # FK: reviewer_id -> User (empty until reviewed)
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_flags'
    )
    flagged_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)  # empty until reviewed


class ApiUsage(models.Model):
    CALL_TYPE_CHOICES = [
        ('Transcribe', 'Transcribe'),
        ('Reply', 'Reply'),
        ('Hint', 'Hint'),
        ('Translate', 'Translate'),
        ('Opening', 'Opening'),
    ]
    STATUS_CHOICES = [
        ('Reserved', 'Reserved'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Unknown', 'Unknown'),
        ('Validation rejected', 'Validation rejected'),
    ]
    
    environment_id = models.CharField(max_length=50)
    call_type = models.CharField(max_length=20, choices=CALL_TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Reserved')
    
    reserved_usd = models.FloatField(default=0.0)
    estimated_usd = models.FloatField(default=0.0)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
