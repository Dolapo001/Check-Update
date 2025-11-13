# CheckUpdates/wsgi.py (minimal for Vercel)
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CheckUpdates.settings")

# WSGI application exposed as both `app` and `handler` for Vercel's runtime
app = get_wsgi_application()
handler = app
