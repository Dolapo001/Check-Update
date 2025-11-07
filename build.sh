#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Make sure static files are accessible
echo "Build completed - static files should be in $(pwd)/staticfiles"