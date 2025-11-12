"""
WSGI config for CheckUpdates project.
Exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys
import traceback
import logging

# Configure logging to stderr for Vercel
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

# Ensure this matches your project package exactly
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CheckUpdates.settings")

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    # Log full traceback to stderr
    traceback.print_exc(file=sys.stderr)
    logging.error(f"WSGI initialization failed: {str(e)}")
    sys.exit(1)