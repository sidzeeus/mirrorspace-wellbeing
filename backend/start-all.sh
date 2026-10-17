#!/bin/sh
# The whole backend in one container: migrations, first-run content, the Celery worker
# with its scheduler, and the web server. For single-instance hosts such as Render's
# free tier, which has no separate worker service. Multi-container deployments run
# these as separate services instead (docker-compose.yml, infra/).
#
# Limits of this mode: if the worker stops, nothing restarts it until the container
# restarts; and while a free instance sleeps, scheduled jobs (weekly emails) wait.
set -eu

python manage.py migrate --noinput

# Idempotent. Seeded content is unreviewed and stays hidden in production until a
# reviewer approves it in the admin.
python manage.py seed_exercises
python manage.py seed_resources
python manage.py seed_knowledge
python manage.py index_knowledge

# The first admin account, once, from DJANGO_SUPERUSER_EMAIL and
# DJANGO_SUPERUSER_PASSWORD. Unset them after the first deploy.
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py createsuperuser --noinput >/dev/null 2>&1 || echo "admin account already exists"
fi

celery -A config worker --beat --loglevel info --concurrency 1 \
    --schedule /tmp/celerybeat-schedule &

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" --timeout 60 --graceful-timeout 30 \
    --control-socket /tmp/gunicorn.ctl
