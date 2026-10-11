# Progress

Updated at the end of every phase. Each entry says what is done, what is unfinished, and what was assumed.

Current phase: **Phase 3 complete (backend for Phases 1 to 3 done). Frontend (Prompt 4) not started.**

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
- [x] checkins (no free-text note), local date + timezone handling
- [x] episodes and triggers
- [x] wellbeing: exercises, translations, exercise events, seed command
- [x] Patterns endpoint (correlation-only observations)
- [x] Export and deletion cover the new models
- [x] Cross-user access tests for every user-owned resource
- [x] `docs/api.md`

### Phase 3: Safety and sharing (Prompt 3)
- [x] safety: safety plan, resource directory, stale-entry command
- [x] sharing: trusted contacts, double opt-in, unsubscribe, consent records, weekly message generator, preview
- [x] notifications: idempotent Celery tasks, consent re-check at send, retries, bounces, timezone/DST
- [x] SOS notify-contact with explicit confirmation and rate limits
- [x] audit: consent and security events, pseudonymization on deletion
- [x] `docs/privacy.md`

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

### 2026-10-12: Phase 2 (Core wellbeing)

Done
- `backend/apps/checkins`: `CheckIn` (one per user per local day, structured fields only, database range and not-empty constraints), `dates.py` (local date from the zone database), `patterns.py` and `GET /api/v1/patterns`.
- `backend/apps/episodes`: `Trigger` and `Episode`, with `label` and `what_helped` encrypted at rest. An episode can only point at the owner's own trigger.
- `backend/apps/wellbeing`: `Exercise`, `ExerciseTranslation`, `ExerciseEvent`; only approved content is served; `python manage.py seed_exercises` loads six placeholders as `needs_review`.
- `backend/config/fields.py`: `EncryptedTextField` with key rotation. `backend/config/views.py`: `OwnedModelViewSet`.
- `GET /api/v1/export` with a registry (`apps/accounts/export.py`) that each app adds a section to.
- `docs/api.md` documents every route with examples and error cases.

Verified on 2026-10-12
- 290 tests pass on PostgreSQL 16, 97% coverage; ruff, ruff format, mypy clean; no missing migrations; OpenAPI schema generates with no warnings; `check --deploy` clean.
- Cross-user contract (`OwnedResourceContract`) passes for check-ins, triggers, episodes and exercise events.
- `tests/test_data_coverage.py` discovers user-owned models by introspection and fails if one is missing from the export or would survive account deletion.
- Canary-string test: trigger labels and "what helped" text do not appear in logs.

Unfinished or not verified
- The CI workflow still has not run on GitHub (no remote).
- No Hindi exercise text exists; the language fallback is tested with fixture data only.
- Episode list has no date filter yet; add if the frontend needs it.

Assumptions
- Recorded as B13 to B20 and Q9 in `docs/decisions.md`.

Needs human review
- R1 and R10 now point at real placeholder content. R17 (scale meanings) and R18 (encryption key procedure) added.

### 2026-10-12: Phase 3 (Safety and sharing)

Done
- `backend/apps/safety`: `SafetyPlan` (one per user, encrypted, no id in the URL) and `Resource` (served only once verified; `stale` flag). Commands `seed_resources` and `flag_stale_resources`.
- `backend/apps/sharing`: `TrustedContact` (encrypted, double opt-in), `SuppressedAddress` (do-not-email fingerprints), `ConsentRecord`; `weekly.py` (the four-field note), `schedule.py` (zone-aware send times), `sos.py`, `tokens.py`, `notices.py`.
- `backend/apps/notifications`: `Notification` with a unique idempotency key; `services.attempt` (consent re-check, at-most-once send, retries, bounces); provider adapter; planner and sweeper tasks; bounce webhook.
- `backend/apps/audit`: `AuditEvent`, `record`, `pseudonymize_user`, `purge_expired`. Account flows now write audit events.
- `docs/privacy.md` and the Phase 3 section of `docs/api.md`.

Verified on 2026-10-12
- 521 tests pass on PostgreSQL 16, 98% coverage; ruff, ruff format, mypy clean; no missing migrations; OpenAPI schema generates with no warnings; `check --deploy` clean.
- Every test named in Prompt 3 exists: no email without active consent; consent revoked, paused, contact unsubscribed or removed between scheduling and sending; duplicate task delivery; bounce handling; time zone and DST; unsubscribe; double opt-in; SOS explicit confirmation and rate limits; cross-user contracts for safety plan, contacts, consents and notifications.
- Weekly note: the sent email is compared byte for byte with one built from the four allowed fields; the collector is shown to run only a COUNT and a name lookup.
- Live on the Docker stack with a real worker: one invitation; consent refused before acceptance; one weekly note although the planner ran twice; one SOS email although the request was sent twice; one-click unsubscribe withdrew consent; no private text in structured logs; after account deletion zero owned rows remained and 13 audit rows were pseudonymized.

Bugs the tests caught during this phase (all fixed)
- A contact's email address could be changed with PATCH (a declared serializer field ignores `read_only_fields`).
- The "time zone changed, reschedule" signal handler was held by a weak reference and silently disconnected.

Unfinished or not verified
- The CI workflow still has not run on GitHub (no remote).
- No real email provider is connected. Delivery was verified with Django's SMTP error types and the console backend, not against a provider API.
- The bounce webhook is generic; a provider-specific adapter is needed once one is chosen (R22).
- Invitation, weekly and SOS emails are plain text and English only.
- Admin MFA and infrastructure-level rate limiting remain for the hardening phase.

Assumptions
- Recorded as B21 to B37 and Q10, Q11 in `docs/decisions.md`.

Needs human review
- R2, R4, R5, R6, R8 now point at real placeholder content. R19 to R22 added.
