#!/usr/bin/env bash
set -o errexit  # exit on error

# Create logs directory if it doesn't exist
mkdir -p logs

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Apply migrations
python manage.py migrate

# Create superuser if it doesn't exist
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="${DJANGO_SUPERUSER_USERNAME}").exists():
    User.objects.create_superuser(
        username="${DJANGO_SUPERUSER_USERNAME}",
        email="${DJANGO_SUPERUSER_EMAIL}",
        password="${DJANGO_SUPERUSER_PASSWORD}"
    )
EOF
