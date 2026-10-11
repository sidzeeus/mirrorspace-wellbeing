# Progress

Updated at the end of every phase. Each entry says what is done, what is unfinished, and what was assumed.

Current phase: **Prompt 0 complete. Phase 1 not started.**

## Phase checklist

### Prompt 0: Bootstrap
- [x] Monorepo layout
- [x] `CLAUDE.md` with the 8 non-negotiables and locked decisions
- [x] `docs/decisions.md`, `docs/progress.md`, `docs/review-needed.md`
- [x] Placeholder `docker-compose.yml`, `Dockerfile.backend`, `.env.example`

### Phase 1: Foundation (Prompt 1)
- [ ] Django + DRF project, split settings, custom user model before the first migration
- [ ] PostgreSQL, session auth + CSRF, strict CORS, explicit DRF defaults
- [ ] OpenAPI schema, health and readiness endpoints
- [ ] Structured logging with redaction filter, Sentry wiring with PII scrubbing
- [ ] accounts: register (18+), verify email, login/logout, password reset, session expiry, deletion request
- [ ] docker-compose (web, worker, beat, db, redis, frontend), `Dockerfile.backend`, `.env.example`
- [ ] CI on pull request: ruff, type-check, backend tests, frontend lint/type-check/build
- [ ] Tests, including the reusable cross-user access harness
- [ ] `manage.py check --deploy` clean under production settings

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
