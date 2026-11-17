import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speako.settings')
application = get_wsgi_application()

from practice import providers  # noqa: E402  (apps must be loaded first)
providers.preload_speech_model()
