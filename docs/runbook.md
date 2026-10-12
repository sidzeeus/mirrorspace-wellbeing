# Runbook

How to deploy, roll back, migrate, back up, restore and respond to incidents.

> **Status.** The procedures below were rehearsed on one machine with the production images and settings (see "Rehearsal record"). They have not been run against a real hosted environment, because none exists yet (decisions.md Q3). Treat the first real deploy as a rehearsal too, and correct this file as you go.

## The pieces

| Piece | What runs it | Notes |
|---|---|---|
| API | `web` container: gunicorn, 3 workers, port 8000 | Behind the host's TLS-terminating reverse proxy |
| Worker | `worker` container: Celery | Sends email, erases deleted accounts |
| Scheduler | `beat` container: Celery Beat | **Exactly one** must run, or scheduled jobs fire twice |
| Frontend | `frontend` container: Next.js, port 3000 | Proxies `/api/v1` to the API |
| Database | Managed PostgreSQL 16 with the `vector` extension | Holds everything |
| Queue and cache | Managed Redis | Holds task ids and rate-limit counters only |

Images live in GitHub Container Registry as `ghcr.io/<owner>/<repo>-backend` and `-frontend`, tagged `sha-<full commit>`. A `v*` Git tag adds a release tag. There is no `latest` tag.

## Configuration and secrets

Every variable is documented in `.env.example`. In production they come from the host's secret store, written to the file named by `ENV_FILE`. Nothing secret is in Git, in an image, or in a workflow log.

Required in production (the API refuses to start without them):

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Long random value. Rotating it signs everyone out and invalidates emailed links. |
| `DJANGO_ALLOWED_HOSTS` | The public API hostname **and** the internal name the frontend uses to reach the API (`web` in the provided compose file). Without the internal name every request from the app is refused. |
| `FRONTEND_URL`, `API_BASE_URL`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | The real hostnames |
| `DATABASE_URL`, `REDIS_URL` | Managed services |
| `DEFAULT_FROM_EMAIL` and the `EMAIL_*` settings | A verified sending domain |
| `FIELD_ENCRYPTION_KEYS` | **If lost, trigger names, "what helped", safety plans, contact details and saved chats are unreadable for ever.** Back it up separately from the database. |
| `PSEUDONYM_KEY` | **Must never change once in use**, or the do-not-email list stops matching. Back it up. |
| `ANTHROPIC_API_KEY` | Only if the chat uses the Anthropic provider |
| `NUM_PROXIES` | Number of trusted proxies in front of the API: normally 2 (the host's load balancer and the frontend proxy). Wrong value means rate limits count the wrong address. |

Recommended: `SENTRY_DSN`, `RELEASE` (set to the commit), `EMAIL_WEBHOOK_SECRET`, `DJANGO_ADMIN_URL` (something unguessable).

### Rotating the field-encryption key

1. Generate a new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Put it **first** in `FIELD_ENCRYPTION_KEYS`, keeping the old key after it: `new,old`. Deploy. New writes use the new key; old data still reads.
3. Re-save existing rows so they are re-encrypted (a management command for this is not written yet: open work).
4. Only after step 3 is complete and verified, remove the old key.

## Deploy

Images are built and published automatically for every commit on `main` (`.github/workflows/release.yml`), after the image scan and dependency audit pass.

To deploy a commit: GitHub, Actions, **Deploy**, Run workflow. Choose the environment and paste the full commit SHA. Production requires an approval (configured on the GitHub environment).

What it does, in order (`infra/deploy.sh`):

1. Pulls the two images for that exact commit.
2. Runs `python manage.py migrate` with the new image while the old version is still serving.
3. Replaces the API, worker, scheduler and frontend, and waits for health checks.
4. Runs `infra/smoke-test.sh`. On failure it stops and prints the rollback command.

By hand on the host:

```bash
REGISTRY=ghcr.io/<owner>/<repo> ENV_FILE=/etc/wellbeing/production.env \
API_URL=https://api.example.com APP_URL=https://app.example.com \
sh infra/deploy.sh <full-commit-sha>
```

### Before every release

- [ ] CI is green on that commit, including the browser tests.
- [ ] `python manage.py flag_stale_resources --fail-on-stale` passes: **no helpline shown to students is stale** (see "Helplines").
- [ ] Nothing new is waiting in `docs/review-needed.md` for content this release exposes.
- [ ] Migrations in this release are backwards compatible (see "Migrations").
- [ ] A recent backup exists.

### After a deploy

- Smoke tests passed (the workflow runs them from the host and from outside).
- `GET /api/v1/ready` answers 200.
- Worker logs show `ready`; exactly one scheduler is running.
- For the first deploy only: create the first admin user (`python manage.py createsuperuser`), load content if wanted (`seed_exercises`, `seed_resources`, `seed_knowledge`, then `index_knowledge`). Seeded content is unreviewed and stays hidden until approved.

## Rollback

Code:

```bash
sh infra/deploy.sh <previous-commit-sha>
```

The previous commit is recorded on the host in `/var/lib/wellbeing/previous`.

Database: migrations are **not** undone automatically. Because every migration must be backwards compatible, the previous code runs against the newer schema, so rolling back code alone is normally enough. If a migration itself is the problem, write a new forward migration that fixes it. Restore from backup only as a last resort: it loses everything written since the backup.

## Migrations

Rules, because migrations run while the old version is still serving:

- **Add first, remove later.** Adding a table or a nullable column is safe. Removing or renaming something the running version uses is not: do it in a later release, after no deployed code refers to it.
- A new non-null column needs a default, or two releases (add nullable, backfill, then tighten).
- Large data changes go in a separate, resumable step, not in the deploy.
- CI fails if a model change has no migration (`makemigrations --check`).
- Never edit a migration that has been deployed.

The `chat` app's first migration creates the `vector` extension. On a managed database the migration user may not be allowed to; if so, have an administrator run `CREATE EXTENSION IF NOT EXISTS vector;` once.

## Backup and restore

What to back up:

| What | How | Kept |
|---|---|---|
| PostgreSQL | The provider's automated daily backups with point-in-time recovery | 30 days suggested (needs a decision; affects how long deleted data lingers in backups) |
| `FIELD_ENCRYPTION_KEYS`, `PSEUDONYM_KEY` | The secret manager, versioned, and one offline copy | For as long as any data encrypted with them exists |
| Redis | Nothing. It holds queue entries and counters. Durable state (deletion requests, notifications) is in PostgreSQL. | |

**A database backup without the encryption key cannot be fully read, and the key without the backup is useless. Store them apart.**

Deleted accounts: a deleted student's data remains inside backups until those backups expire. Say so in the privacy notice (review-needed R8). After restoring a backup, re-apply any account deletions requested since it was taken; the audit trail records that deletions happened, pseudonymously, but not for whom, so keep a short-lived operational record of deletion requests if this matters (open decision).

Restore rehearsal, monthly (a reminder issue is opened automatically):

1. Restore the latest backup into a **separate** scratch database.
2. Compare row counts with production.
3. Start the API against the scratch database with the production keys and confirm an encrypted field can be read.
4. Drop the scratch database. Record the date and result below.

Locally this is one command, and it is the same procedure: `sh infra/backup-restore-rehearsal.sh`.

### Rehearsal record

| Date | Where | Result | By |
|---|---|---|---|
| 2026-10-12 | Local Docker stack, development data | Passed: dump restored, 32 tables with identical row counts, encrypted fields decrypted | Engineer (Claude) |
| | First hosted environment | Not done yet | |

## Helplines

**A named person is responsible for the helpline directory. That person is not yet assigned (decisions.md Q7). Do not launch until they are.**

- Every entry has an owner, a source and a `verified_on` date. Only entries with status `approved` are shown.
- An entry is stale 90 days after verification (`RESOURCE_MAX_AGE_DAYS`). Stale entries are still shown, visibly flagged.
- Every Monday a reminder issue is opened. The owner checks each number against its official source, updates the entry in the admin, and sets `verified_on`.
- **Before every release**, run `python manage.py flag_stale_resources --fail-on-stale`. A non-zero exit blocks the release.
- Code never changes a number and never approves an entry.

The same discipline applies to exercises and chat knowledge: nothing is shown or quoted until a qualified reviewer sets it to `approved`, and after changing knowledge documents run `python manage.py index_knowledge`.

## Scheduled jobs

Run by the scheduler container (`CELERY_BEAT_SCHEDULE` in `backend/config/settings/base.py`):

| Job | When | What |
|---|---|---|
| `notifications.enqueue_due_weekly` | Every 10 minutes | Plans a weekly note for each active consent that is due |
| `notifications.sweep_stuck` | Every 10 minutes | Marks sends that never finished as failed (never re-sends) |
| `accounts.purge_stale_accounts` | Hourly | Finishes account deletions whose task was lost; removes accounts unverified after 7 days |
| `chat.purge_expired` | Hourly | Deletes saved chats past their retention date |
| `accounts.clear_expired_sessions` | Daily | Removes expired sessions |
| `audit.purge_expired` | Daily | Removes audit events older than 12 months |

## Incidents

First, for any incident: note the time, what you saw, and what you did. Do not paste student data into chat tools or tickets.

| Situation | Do |
|---|---|
| **The app is down** | Check `/api/v1/health` (process) and `/api/v1/ready` (database, Redis). Check the host and the managed services. Roll back if a deploy just happened. Support, the saved safety plan and helplines keep working offline for people who have opened the app before. |
| **Emails are not going out** | Check worker logs for `notification_failed` or `notification_gave_up` (ids only). Check the provider's status and the sending domain. Failed notifications are **not** retried automatically after 5 attempts, by design. Students see the status under Sharing. |
| **Emails went to the wrong person, or a note was sent that should not have been** | Pause sending: stop the `worker` container. Find the cause before restarting. Treat as a personal-data incident (below). |
| **A wrong helpline number is live** | In the admin set the entry to `retired` immediately (it disappears from the app; offline copies update on next connection). Then correct and re-verify it. |
| **The chat says something it should not** | Set `CHAT_PROVIDER=apps.chat.providers.MockProvider` and redeploy, or remove chat from the frontend, to turn the model off. The fixed safety replies do not depend on the model. Add the case to `apps/chat/evaluation/cases.json` and fix the check. |
| **Suspected break-in or leaked secret** | Rotate the affected secret now. `DJANGO_SECRET_KEY`: signs everyone out. Database password and Redis URL: rotate at the provider. `ANTHROPIC_API_KEY` and email credentials: rotate at the provider. Do **not** change `PSEUDONYM_KEY`. If `FIELD_ENCRYPTION_KEYS` leaked, add a new key first in the list and plan re-encryption. Review the audit trail and the provider's access logs. |
| **Personal data may have been exposed** | This may be a notifiable breach under India's DPDP Act. Contact the privacy lawyer immediately (review-needed R6). Preserve logs. Do not delete evidence. |
| **A student reports being in danger** | The app is not an emergency service and nobody monitors it. Whoever receives the report should direct the person to local emergency services and verified helplines. A human response process must be defined by a safeguarding lead before launch (review-needed R14). There is none today. |

## Useful commands

On the host, with the same environment variables as `deploy.sh`:

```bash
docker compose -f infra/docker-compose.production.yml ps
```

```bash
docker compose -f infra/docker-compose.production.yml logs --since 15m worker
```

```bash
docker compose -f infra/docker-compose.production.yml exec web python manage.py flag_stale_resources
```

Logs are one JSON object per line. They contain event names and ids, never message text, names or addresses. To follow one notification, search for its id.

## Rehearsing a deploy on one machine

Runs the production images and settings with a throwaway database:

```bash
docker compose -f infra/docker-compose.production.yml -f infra/docker-compose.staging-local.yml up -d --wait
```

It needs `BACKEND_IMAGE`, `FRONTEND_IMAGE` and `ENV_FILE` set. The steps used for the rehearsal on 2026-10-12 are recorded in `docs/progress.md`.
