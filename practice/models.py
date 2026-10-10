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
