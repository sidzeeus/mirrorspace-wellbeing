#!/bin/sh
# The whole backend in one container: migrations, the web server, first-run content, and
# the Celery worker with its scheduler. For single-instance hosts such as Render's free
# tier, which has no separate worker service. Multi-container deployments run these as
# separate services instead (docker-compose.yml, infra/).
#
# A free instance sleeps when idle and every wake-up runs this script on a very small
# CPU, so the web server starts as early as possible: only migrations come before it.
# Everything else waits in the background until it is up.
#
# Limits of this mode: if the worker stops, nothing restarts it until the container
# restarts; and while a free instance sleeps, scheduled jobs (weekly emails) wait.
set -eu

python manage.py migrate --noinput

(
    sleep 15
    # One Django start for all of it. Idempotent: seeded content is unreviewed and stays
    # hidden in production until a reviewer approves it in the admin. The admin account
    # is created once from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD.
    nice python manage.py shell -c "
import os
from django.core.management import call_command
for command in ('seed_exercises', 'seed_resources', 'seed_knowledge', 'index_knowledge'):
    call_command(command)
if os.environ.get('DJANGO_SUPERUSER_EMAIL') and os.environ.get('DJANGO_SUPERUSER_PASSWORD'):
    from apps.accounts.models import User
    if not User.objects.filter(email__iexact=os.environ['DJANGO_SUPERUSER_EMAIL']).exists():
        call_command('createsuperuser', interactive=False)
" || echo "first-run content step failed; the app keeps running"

    exec nice celery -A config worker --beat --loglevel info --concurrency 1 \
        --schedule /tmp/celerybeat-schedule
) &

# One process that loads Django once (--preload), with threads for concurrency: on a
# tiny CPU this starts far faster than several worker processes.
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" \
    --preload --workers "${WEB_CONCURRENCY:-1}" --threads 4 \
    --timeout 60 --graceful-timeout 30 --control-socket /tmp/gunicorn.ctl
