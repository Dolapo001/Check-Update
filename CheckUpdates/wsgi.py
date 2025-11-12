"""
WSGI config for CheckUpdates project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys
import traceback

# Ensure this matches your project package exactly (case-sensitive)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CheckUpdates.settings")

try:
    # Keep imports lazy and minimal — avoid importing extra packages here.
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception:
    # Print full traceback so your deployment logs show the real error
    traceback.print_exc()
    # Exit explicitly so platform marks the failure and you get logs
    sys.exit(1)
