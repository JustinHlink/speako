import uuid
from django.db import models


class PracticeSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turns = models.JSONField(default=list)
    pending = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='in_progress')
    busy = models.BooleanField(default=False)
    summary = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class ApiAttempt(models.Model):
    purpose = models.CharField(max_length=20)
    status = models.CharField(max_length=30, default='reserved')
    elapsed_ms = models.FloatField(default=0)
    prompt_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    # A conservative reservation remains even when token usage is unavailable.
    guard_usd = models.FloatField(default=0.02)
    created_at = models.DateTimeField(auto_now_add=True)

class Flag(models.Model):
    STATUS_CHOICES = [
        ('unresolved', 'Unresolved'),
        ('accepted', 'Accepted'),
        ('incorrect', 'Incorrect'),
    ]

    text = models.TextField()
    ai_reply = models.TextField()
    reason = models.TextField(blank=True, default='') # Can be deleted if not needed

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unresolved')
    reviewer_id = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Flag {self.id} - {self.status}"


