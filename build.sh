#!/usr/bin/env bash
set -o errexit

# Create logs directory if it doesn't exist
mkdir -p logs

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate