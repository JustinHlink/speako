"""Reviewer web page; the existing review APIs remain the authorization boundary."""
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from .views import require_role

@require_GET
@require_role(['Reviewer'])
@ensure_csrf_cookie
def page(request):
    return render(request, 'practice/reviewer.html')
