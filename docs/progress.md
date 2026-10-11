# Progress

Updated at the end of every phase. Each entry says what is done, what is unfinished, and what was assumed.

Current phase: **Phase 1 complete. Phase 2 not started.**

## Phase checklist

### Prompt 0: Bootstrap
- [x] Monorepo layout
- [x] `CLAUDE.md` with the 8 non-negotiables and locked decisions
- [x] `docs/decisions.md`, `docs/progress.md`, `docs/review-needed.md`
- [x] Placeholder `docker-compose.yml`, `Dockerfile.backend`, `.env.example`

### Phase 1: Foundation (Prompt 1)
- [x] Django + DRF project, split settings, custom user model before the first migration
- [x] PostgreSQL, session auth + CSRF, strict CORS, explicit DRF defaults
- [x] OpenAPI schema, health and readiness endpoints
- [x] Structured logging with redaction filter, Sentry wiring with PII scrubbing
- [x] accounts: register (18+), verify email, login/logout, password reset, session expiry, deletion request
- [x] docker-compose (web, worker, beat, db, redis, frontend), `Dockerfile.backend`, `.env.example`
- [x] CI workflow: ruff, type-check, backend tests, frontend lint/type-check/build, image build
- [x] Tests, including the reusable cross-user access harness
- [x] `manage.py check --deploy` clean under production settings

### Phase 2: Core wellbeing (Prompt 2)
- [ ] checkins (no free-text note), local date + timezone handling
- [ ] episodes and triggers
- [ ] wellbeing: exercises, translations, exercise events, seed command
- [ ] Patterns endpoint (correlation-only observations)
- [ ] Export and deletion cover the new models
- [ ] Cross-user access tests for every user-owned resource
- [ ] `docs/api.md`

### Phase 3: Safety and sharing (Prompt 3)
- [ ] safety: safety plan, resource directory, stale-entry command
- [ ] sharing: trusted contacts, double opt-in, unsubscribe, consent records, weekly message generator, preview
- [ ] notifications: idempotent Celery tasks, consent re-check at send, retries, bounces, timezone/DST
- [ ] SOS notify-contact with explicit confirmation and rate limits
- [ ] audit: consent and security events, pseudonymization on deletion
- [ ] `docs/privacy.md`

### Frontend (Prompts 4, 5a to 5e, 6)
- [ ] 4: Design plan, tokens, themes, typography, core components, the Lumen, landing page
- [ ] 5a: Auth screens, app shell, onboarding, dashboard
- [ ] 5b: Check-in, patterns, episodes and triggers
- [ ] 5c: Exercise library and players
- [ ] 5d: Support (SOS), safety plan, resources, offline PWA cache
- [ ] 5e: Sharing, consent history, privacy settings
- [ ] 6: Localization, full PWA, accessibility hardening, bundle budget

### Phase 4: AI support chat (Prompt 7)
- [ ] Provider adapter, budgets and rate limits
- [ ] Curated knowledge pipeline with pgvector, approved content only
- [ ] Chat policy and deterministic crisis workflow as separate code
- [ ] Chat UI
- [ ] Evaluation set with mocked provider

### Phase 5: Hardening (Prompt 8)
- [ ] Security baseline review, dependency audit
- [ ] Route-enumeration test (auth, ownership, cross-user test exists)
- [ ] Retention, deletion and export verification
- [ ] Canary-string tests for logs, task names, Sentry
- [ ] Load check, backup and restore rehearsal
- [ ] `docs/security-review.md`

### Phase 6: Deployment (Prompt 9)
- [ ] Production images, graceful shutdown
- [ ] GitHub Actions: PR, main (build, scan, publish to GHCR), deploy, scheduled checks
- [ ] `docs/runbook.md`

### Final
- [ ] Final review (Prompt 10): PASS / FAIL / NEEDS_HUMAN_REVIEW table
- [ ] `docs/MY_GUIDE.md`

## Log

### 2026-10-12: Prompt 0
Done: repository skeleton, `CLAUDE.md`, decisions, progress and review-needed documents, placeholder infrastructure files. No feature code.

Unfinished: everything from Phase 1 onward.

Assumptions: recorded as B1 to B3 and Q1 to Q8 in `docs/decisions.md`.

Tests: none exist yet.

### 2026-10-12: Phase 1 (Foundation)

Done
- `backend/config`: split settings, session auth with CSRF on every write (including anonymous sign-in and registration), CORS allowlist, explicit DRF defaults, JSON logs behind `RedactionFilter`, Sentry scrubbing (`scrub_sentry_event`), `/api/v1/health`, `/api/v1/ready`, `/api/v1/schema`.
- `backend/apps/accounts`: `User` (UUID, email login) and `Profile`; register, verify email, resend, login, logout, me, password reset, account deletion; background tasks that take IDs only.
- `backend/tests/harness.py`: `OwnedResourceContract`, the cross-user access contract every later app reuses. `tests/test_harness.py` proves it fails against a deliberately leaky endpoint.
- Docker: pinned images, non-root users, compose stack of six services, documented `.env.example`.
- `.github/workflows/ci.yml`.
- Minimal Next.js shell (placeholder page only; the real frontend starts at Prompt 4).

Verified on 2026-10-12
- Backend: 126 tests pass on PostgreSQL 16; 95% coverage; ruff, ruff format and mypy clean; no missing migrations.
- `check --deploy --fail-level WARNING` passes under production settings (on the host and inside the Linux image).
- `docker compose up --build --wait` with only `.env.example` present: all services healthy. A live register, verify, sign-in, delete flow succeeded and the row was erased by the worker.
- Backend image under production settings: gunicorn runs as uid 10001, both probes pass, stops cleanly on SIGTERM in 3 seconds.
- Frontend: lint, type-check and build pass; production image serves 200 as the `node` user.

Unfinished or not verified
- The CI workflow has not run on GitHub: the repository has no remote yet. Every command in it was run locally.
- "Clean clone" was checked from the working tree with no `.env` file, not from a second fresh clone.
- Data export (`GET /api/v1/export`) is not built yet; it arrives with the first user data in Phase 2.
- No audit trail yet for account events; the audit app is Phase 3.
- Operator MFA for the admin is not configured (hardening, Phase 5).

Assumptions
- Recorded as B4 to B12 in `docs/decisions.md`.
- Local settings turn off Celery's stdout redirection so the console email backend shows the confirmation link; everywhere else worker output goes through the redaction filter.

Needs human review
- R15 (account email wording) and R16 (password and session rules) added to `docs/review-needed.md`.
