# Progress

Updated at the end of every phase. Each entry says what is done, what is unfinished, and what was assumed.

Current phase: **All build phases complete (Phases 1 to 6 and the final review). Not ready for real students: see `docs/final-review.md`.**

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
- [x] 4: Design plan, tokens, themes, typography, core components, the Lumen, landing page
- [x] 5a: Auth screens, app shell, onboarding, dashboard
- [x] 5b: Check-in, patterns, episodes and triggers
- [x] 5c: Exercise library and players
- [x] 5d: Support (SOS), safety plan, resources, offline PWA cache
- [x] 5e: Sharing, consent history, privacy settings
- [x] 6: Localization, full PWA, accessibility hardening, bundle budget

### Phase 4: AI support chat (Prompt 7)
- [x] Provider adapter, budgets and rate limits
- [x] Curated knowledge pipeline with pgvector, approved content only
- [x] Chat policy and deterministic crisis workflow as separate code
- [x] Chat UI
- [x] Evaluation set with mocked provider

### Phase 5: Hardening (Prompt 8)
- [x] Security baseline review, dependency audit
- [x] Route-enumeration test (auth, ownership, cross-user test exists)
- [x] Retention, deletion and export verification
- [x] Canary-string tests for logs, task names, Sentry
- [x] Load check, backup and restore rehearsal
- [x] `docs/security-review.md`

### Phase 6: Deployment (Prompt 9)
- [x] Production images, graceful shutdown
- [x] GitHub Actions: PR, main (build, scan, publish to GHCR), deploy, scheduled checks
- [x] `docs/runbook.md`

### Final
- [x] Final review (Prompt 10): PASS / FAIL / NEEDS_HUMAN_REVIEW table
- [x] `docs/MY_GUIDE.md`

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

### 2026-10-12: Frontend (Prompts 4, 5a to 5e, 6)

Done
- `docs/design-plan.md`: tokens, type scale, wireframes, and the self-review against generic defaults with what changed.
- Design system: `frontend/src/app/globals.css` (Night and Daybreak tokens, radii by hierarchy, crop marks, glass with a solid fallback, reduced-motion rules), `components/ui/primitives.tsx` and `components/ui/controls.tsx` (Radix-based).
- The Lumen: `components/lumen/` (static SVG, WebGL, Canvas 2D, frame-rate guard). Documented in `docs/lumen.md`.
- Screens: landing, helplines, sign in, register, verify email, forgot and reset password, onboarding, home, check-in, patterns, episodes and triggers, exercises, exercise and breathing player, safety plan, Support, sharing, consent history, settings, More, contact invitation, unsubscribe, offline.
- `frontend/src/app/api/v1/[...path]/route.ts`: same-origin proxy to the API.
- PWA: `public/sw.js`, `app/manifest.ts`, icons, update prompt, offline page.
- Localization: every string in `frontend/messages/en/*.json`; partial placeholder Hindi in `messages/hi/`; `docs/localization.md` with the fluent-speaker review script.
- CI: copy-rule unit tests, and a browser job that runs Playwright with axe and the bundle budget against the compose stack.

Verified on 2026-10-12
- 62 Playwright tests pass against the production build and the real API. They cover every flow named in the prompts: sign up to dashboard; check in to trend; complete an exercise and mark it not helpful; the SOS send path and the cancel path; Support offline; opt in, contact confirms, preview, confirm, revoke; sharing off by default.
- axe (WCAG 2.2 AA rules) reports no violations on every screen, in both themes, at phone and desktop widths.
- 7 copy-rule unit tests pass: banned wording in observations, no clinical labels, no streaks or praise, no monitoring claims, sentence case, translation keys.
- Lighthouse, mobile, production build: landing performance 92, accessibility 100; Support 91 and 100; sign in 89 and 100.
- Compressed JavaScript: landing 188 KB, Support 228 KB, sign in 233 KB (budgets 260, 290, 280).
- No screen scrolls sideways at 320px with larger text, in English or Hindi.
- Screenshots of the landing page in both themes at phone and desktop widths are in `docs/screenshots/`.

Bugs the tests caught (all fixed)
- The full-screen exercise player sat underneath the navigation bar.
- The check-in confirmation could vanish because the form rebuilt itself after saving.
- The landing header overflowed on a 320px phone with larger text; long display names pushed the home screen sideways.
- The saved safety plan was unreachable offline on the Plan screen because the session check could not run.

Unfinished or not verified
- Sign in scores 89 on Lighthouse performance, one point under the 90 target for core screens. The landing page meets it.
- No test on a real low-end Android phone or with a real screen reader. Automated checks only; the manual pass is in `docs/localization.md` section 4 and still to do.
- The browser job in CI has not run on GitHub (no remote).
- Hindi is partial and unreviewed.
- The Lumen's frame-rate guard is not exercised by a test on a slow device.

Assumptions
- Recorded as B38 to B47 in `docs/decisions.md`.

Needs human review
- Every string on the Support, safety plan, helplines, sharing and contact screens is listed in `docs/review-needed.md` under "String checklists" (generated by `frontend/scripts/string-checklist.mjs`).

### 2026-10-12: Phase 4 (AI support chat)

Done
- `backend/apps/chat`: `safety.py` (the crisis check, in code), `policy.py` (instructions, fixed replies, output check), `knowledge.py` (chunking, local embedding, retrieval over pgvector), `providers.py` (`MockProvider`, `AnthropicProvider`), `services.py` (the five-step pipeline, budgets, transcripts), models, API, `seed_knowledge` and `index_knowledge` commands.
- `apps/chat/evaluation/cases.json`: 58 cases across grounded, unsupported, self-harm, panic, abuse, code-switched, misspelled, prompt injection, provider outage and rate limit.
- `frontend/src/app/(app)/chat/page.tsx`: the "I am an AI" banner, limits, opt-in saving, sources, feedback, and fixed safety replies with routes to Support.

Verified on 2026-10-12
- 655 backend tests pass, 98% coverage; ruff and mypy clean. Every evaluation case passes with the mocked provider.
- Every crisis case returns the fixed reply, never reaches the provider, and creates no notification.
- A crisis message is still answered when the budget is exhausted and when the provider is down.
- Tests inspect the provider request (no identity or records), the logs and audit trail (no prompt or reply text), and the Sentry scrubber.
- 4 chat browser tests pass, with no axe violations.

Unfinished or not verified
- **No real model has been called.** `AnthropicProvider` is tested against a faked SDK only. Answer quality, latency and cost with the real model are unknown (R24).
- The safety patterns are an engineer's list. Their false-positive and false-negative rates on real student wording are unmeasured (R3).
- Retrieval matches shared vocabulary, not meaning, so a question phrased with different words than the material gets the "no reviewed material" reply.
- The knowledge base has four placeholder documents, in English only.
- Chat replies are not streamed.

Assumptions
- Recorded as B48 to B56 in `docs/decisions.md`.

Needs human review
- R3 and R12 now point at real placeholder content. R23 and R24 added.

### 2026-10-12: Phase 5 (hardening)

Done
- `tests/test_routes.py`: lists every route and fails if one is neither on the reviewed public list (20 routes) nor covered by an ownership test.
- `tests/test_hardening.py`: production settings, required secrets, no usable secret defaults, canary strings in logs, task arguments and Sentry events.
- `NoStoreApiMiddleware`, a partial Content-Security-Policy and other response headers on the frontend.
- `infra/loadcheck.py` and `infra/backup-restore-rehearsal.sh`.
- `docs/security-review.md`: seven findings fixed (F1 to F7), nine left open (S1 to S9).

Verified on 2026-10-12
- 766 backend tests pass on PostgreSQL, 98% coverage. Ruff, mypy, `makemigrations --check` and `check --deploy` clean.
- 66 browser tests pass with no axe violations. 7 copy-rule tests pass.
- `pip-audit` and `npm audit --omit=dev`: no known vulnerabilities.
- Backup and restore rehearsal: 32 tables restored with identical row counts, encrypted fields readable.
- Load check on the development server: health p95 29 ms, ready 115 ms, signed-in reads 240 to 380 ms.

Unfinished or not verified
- The load figures come from a laptop and a development server. They say nothing about a real host.
- No independent security test. No multi-factor sign-in for the admin (S1). No edge rate limiting (S2). Script policy still allows inline scripts (S3).
- Sentry scrubbing is tested on constructed events, not against a live project (S6).

Assumptions
- Recorded as B57, B58 and B62 in `docs/decisions.md`.

### 2026-10-12: Phase 6 (deployment)

Done
- `Dockerfile.backend` and `frontend/Dockerfile`: pinned base images, non-root users, health checks, graceful stop.
- `infra/docker-compose.production.yml`, `infra/deploy.sh`, `infra/smoke-test.sh`.
- Workflows: `ci.yml` (tests, lint, types, browser tests), `release.yml` (build, scan, publish to GHCR as `sha-<commit>`), `deploy.yml` (manual, by commit, with approval for production), `scheduled.yml` (weekly audit, helpline and restore reminders), and `dependabot.yml`.
- `docs/runbook.md`.

Staging rehearsal on one machine, 2026-10-12
1. Built both images and tagged them `sha-<commit>`. Neither is tagged `latest`; both run as a non-root user.
2. Wrote a throwaway environment file with freshly generated secrets, `config.settings.production` and the mock chat provider.
3. Started PostgreSQL and Redis from `infra/docker-compose.production.yml` plus `infra/docker-compose.staging-local.yml`.
4. Ran migrations with the new image (`--profile migrate run --rm migrate`).
5. Ran `manage.py check --deploy --fail-level WARNING` inside the image: no issues.
6. Started the API, worker, scheduler and frontend and waited for their health checks.
7. Ran `infra/smoke-test.sh`: 18 of 18 passed.
8. Stopped the API and worker: both exited cleanly in about 10 seconds.
9. Removed the containers, the volume and the environment file.

Unfinished or not verified
- **No workflow has run.** The repository has no remote, so CI, the image scan, publishing and the deploy workflow are untested. This is the one FAIL in the final review.
- No hosted environment exists (question Q3). The runbook has been rehearsed locally only.
- No real email provider is connected; the bounce webhook is a generic shape awaiting a provider (R22).
- Re-encrypting old rows after a key rotation has no command yet.

Assumptions
- Recorded as B59 to B61 in `docs/decisions.md`.

### 2026-10-12: Final review

- `docs/final-review.md`: 10 Definition of Done items and the 8 non-negotiables, each with evidence. One FAIL (nothing published, because nothing has been pushed). The rest pass in code; helplines, all wording and the chat need human sign-off before any student uses the app.
- `docs/MY_GUIDE.md`: the owner's guide to how everything works.

### 2026-10-12: Frontend restyle after owner feedback

Done
- New visual direction from the owner's four reference images: black background, dithered scenes, hairlines, corner marks, square controls, mono labels, film grain (decisions B63, B64).
- `frontend/src/components/scene/`: `fields.ts` (the pictures, as brightness functions) and `Scene.tsx` (still image first, canvas shimmer where motion is allowed, stops itself on slow devices).
- `frontend/scripts/make-scenes.mjs` writes the stills to `frontend/public/scenes/`.
- Landing page, story, footer, public header and the sign-in family of pages rebuilt. Tokens in `globals.css` changed, so the signed-in screens inherit the black palette and square controls.

Unfinished or not verified
- Signed-in screens only inherit the new tokens; they have not been individually redesigned.
- Not looked at on a real phone.

Explained to the owner, not changed
- Email is not "broken": locally it is printed to the worker log because no email provider is configured (question Q1).
- Chat answers come from the built-in mock because no AI key is configured, and it only answers questions covered by the four placeholder knowledge documents.
