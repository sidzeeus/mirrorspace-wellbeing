# Running and testing locally

## With Docker (the whole stack)

```bash
docker compose up --build
```

This works from a clean clone with the values in `.env.example`. To change a value, copy `.env.example` to `.env` and edit the copy.

| What | Where |
|---|---|
| API health | http://localhost:8000/api/v1/health |
| API readiness (database + Redis) | http://localhost:8000/api/v1/ready |
| OpenAPI schema | http://localhost:8000/api/v1/schema |
| Frontend | http://localhost:3000 |
| Emails (verification, password reset) | printed in the logs: `docker compose logs -f worker` |

Create an admin user:

```bash
docker compose exec web python manage.py createsuperuser
```

## Backend on your machine

PostgreSQL and Redis still come from Docker; Django runs directly.

```bash
docker compose up -d db redis
```

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver
```

On macOS or Linux the interpreter is `.venv/bin/python`.

## Checks

Run from `backend/`:

| Check | Command |
|---|---|
| Tests | `pytest` |
| Lint | `ruff check .` |
| Format | `ruff format --check .` |
| Types | `mypy .` |
| Production configuration | covered by `tests/test_platform.py` (`check --deploy`) |

Run from `frontend/`:

| Check | Command |
|---|---|
| Lint | `npm run lint` |
| Types | `npm run typecheck` |
| Build | `npm run build` |

Tests need PostgreSQL on `localhost:5432` (the `db` service). Redis is not needed for tests: they use an in-memory cache and run background tasks inline.

## Changing dependencies

Edit `backend/requirements.in` or `requirements-dev.in`, then regenerate the pinned files:

```bash
pip-compile --strip-extras --output-file requirements.txt requirements.in
pip-compile --strip-extras --output-file requirements-dev.txt requirements-dev.in
```
