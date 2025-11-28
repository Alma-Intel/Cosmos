#!/bin/bash
# Run migrations and start the server
set -e  # Exit on error

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn server..."
exec gunicorn crm_project.wsgi --bind 0.0.0.0:$PORT --log-file -

