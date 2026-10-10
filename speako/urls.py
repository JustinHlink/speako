from django.urls import path
from practice import views

urlpatterns = [
    path('', views.home),
    path('api/status/', views.status),
    path('api/start/', views.start),
    path('api/transcribe/', views.transcribe),
    path('api/discard/', views.discard),
    path('api/reply/', views.reply),
    path('api/exit/', views.exit_lesson),
    path('api/metrics/', views.metrics),
]
