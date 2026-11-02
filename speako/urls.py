from django.urls import path
from practice import views

urlpatterns = [
    path('', views.home),

    path('api/auth/login/', views.api_login),
    path('api/auth/logout/', views.api_logout),

    path('api/lessons/', views.list_lessons),
    path('api/lessons/<int:lesson_id>/', views.get_lesson_detail),

    path('api/status/', views.status),
    path('api/start/', views.start_lesson),
    path('api/transcribe/', views.transcribe_audio),
    path('api/discard/', views.discard_transcript),
    path('api/reply/', views.submit_reply),
    path('api/exit/', views.exit_lesson),
    path('api/attempts/<uuid:attempt_id>/summary/', views.get_summary),

    path('api/flag/submit/', views.submit_flag),
    path('api/flag/list/', views.list_flags),
    path('api/flag/review/', views.review_flag),

    path('api/metrics/', views.metrics),
]
