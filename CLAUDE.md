# CLAUDE.md

Read this file and `docs/decisions.md` before doing anything else in this repository.

## Project purpose

A privacy-first wellbeing companion for students aged 18 and over. It helps a student notice their own patterns, try small self-help actions, and reach trusted or professional support when they choose to.

It is a support and education prototype. It is **not** therapy, diagnosis, clinical care, or an emergency-monitoring service. Nobody watches the data, and the app never contacts anyone on its own.

`README.md` is the build specification. Precedence: Part A wins for decisions, Part C wins for design, Part E (the blueprint) wins for everything else. Safety and privacy rules in Part E are never relaxed by any prompt.

## The 8 non-negotiables

1. No diagnosis, treatment claims, or promises of suicide prevention anywhere in copy or code.
2. All sharing is **off by default**, explicit, specific, previewable, and revocable.
3. No automatic risk alerts or trusted-contact notifications from a classifier.
4. SOS messages require an explicit user action and show the exact recipient and message first.
5. Never claim the app is monitored, or that an alert was sent, unless that is true and confirmed.
6. No sensitive text (notes, chats, messages) in logs, task names, queue metadata, Sentry, or analytics.
7. Every user-owned query is filtered by the authenticated user. Every such endpoint has a cross-user access test.
8. Clinical content, helpline numbers, the crisis workflow, and legal/privacy copy are placeholders until a qualified human signs them off.

If a request conflicts with any of these, stop and say so. Do not work around them.

## Locked decisions

Rationale and dates are in `docs/decisions.md`. Change decisions there first, then here.

| Topic | Decision |
|---|---|
| Age policy | **18+ only** for the prototype. Age confirmation at registration. No minors' data collected. Revisit only after India-qualified legal review. |
| Authentication | **Django session cookies + CSRF.** Frontend and API on the same site or sibling subdomains with `SameSite=Lax`, `Secure`, `HttpOnly`. No JWT in `localStorage`. Strict CORS allowlist. |
| Weekly contact email content | Only: the student's display name, the week covered, **"checked in X of 7 days"**, and a fixed neutral line. No scores, notes, triggers, chats, or risk labels. The student previews and confirms before the first send and can pause or revoke at any time. |
| Check-in free-text notes | **Omitted in the MVP.** Structured fields only (mood, sleep, energy, stress). If added later: field-encrypted, excluded from logs, exports to email, and chat context. |
| Deletion vs audit retention | On account deletion, all user content is deleted or queued for deletion. Audit and consent events are **pseudonymized** (user ID replaced by a one-way hash, no message bodies) and kept **12 months**, then purged. |
| Trusted-contact flow | **Double opt-in:** the contact receives a confirmation email and must accept before any message is sent. Every email has an unsubscribe link. Rate limits on adding contacts and on SOS sends. |
| Offline safety | Safety plan and verified helpline numbers are available offline via a **PWA service worker** (required, not optional). |
| Automated risk detection | **Out of scope.** No automatic alerts to anyone. Crisis-like chat content triggers a fixed, non-AI safety response showing the user's own safety plan and verified resources. |
| MVP cut line | Build **Phases 1 to 3** first plus their frontend. Chatbot (Phase 4) and Indian-language content come after, but the i18n foundation is built in from the start. |
| Free-text from students to providers | Never sent to analytics or error tracking. Chat content only goes to the AI provider with minimal context, and transcripts are off by default. |
| Languages | English first. Interface built with `next-intl` so Hindi and other Indian languages can be added by translation files only. Reviewed by fluent speakers before release. |

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), TypeScript (strict), Tailwind CSS |
| Frontend libraries | Framer Motion, Radix UI primitives, TanStack Query, Zod + React Hook Form, next-intl, Serwist (PWA), Canvas 2D / WebGL for the Lumen |
| API | Django + Django REST Framework, OpenAPI schema |
| Database | PostgreSQL (pgvector for Phase 4 retrieval) |
| Auth | Django sessions + CSRF, custom user model (UUID pk, email login) |
| Background jobs | Celery + Redis, Celery Beat |
| Email | Transactional provider over SMTP behind an adapter; Mailpit catches everything locally |
| AI (Phase 4) | Hosted LLM behind a provider adapter; mocked in tests |
| Containers | Docker + Docker Compose (web, worker, beat, db, redis, frontend) |
| CI/CD | GitHub Actions, images published to GHCR with immutable Git SHA tags |
| Monitoring | Sentry + structured logs, both with redaction |

Keep it a modular Django monolith with one PostgreSQL database. No Kubernetes, microservices, separate vector database, or model training.

## Repository layout

```text
frontend/            Next.js app
backend/
  config/            Django settings (base/local/test/production), URLs, ASGI/WSGI, Celery
  apps/              accounts, checkins, episodes, wellbeing, safety, sharing,
                     notifications, chat, content_admin, audit
  tests/             cross-app tests (route enumeration, privacy canaries)
infra/               deployment files and scripts
.github/workflows/   CI and deploy pipelines
docs/                decisions, progress, review-needed, api, privacy, runbook
```

## Coding standards

Backend
- Ruff for lint and format. mypy is optional but new code should be typed.
- pytest + pytest-django, DRF `APIClient`, factory_boy. Tests are deterministic and never call a paid provider.
- Every user-owned queryset is scoped in `get_queryset()` by `request.user`. UUIDs are not authorization.
- DRF defaults are explicit: authentication required, throttles set, pagination on. A public endpoint must opt out visibly.
- Timestamps in UTC. The user's timezone is stored and used only for presentation and scheduling.
- Serializers return only the fields the client needs.

Frontend
- ESLint, TypeScript strict, no `any` without a comment explaining why.
- Playwright for browser flows and axe-core for accessibility on every screen.
- Every user-facing string lives in a `next-intl` message file.
- Follow README Part C. WCAG 2.2 AA, 44px touch targets, visible focus, reduced-motion and low-bandwidth fallbacks.
- The persistent Support button is present on every authenticated screen and is never hidden.
- No streaks, guilt copy, confetti, or gamified scores.

Both
- Test first for anything touching users' data: write the cross-user access, consent and ownership tests before or alongside the code.
- Small commits, one logical change each. Never commit secrets, real data, or `.env` files.
- When something is ambiguous, choose the safer and more private option, record it in `docs/decisions.md`, and tell the owner. Never guess silently on consent, privacy or safety behavior.

## Sensitive text rule

**Never put sensitive text in logs, task names, queue metadata, Sentry, or analytics.**

Sensitive text means: safety plan content, episode descriptions, trigger labels, chat prompts and responses, SOS and weekly message bodies, trusted-contact names and addresses, email addresses, tokens, and passwords.

- Log identifiers and event types, never content.
- Celery task arguments are IDs only. The task loads what it needs from the database.
- Error tracking strips request bodies, cookies, headers and local variables.
- Add a canary-string test whenever a new path handles sensitive text.

## Human review

Anything clinical, legal or safeguarding-related is a placeholder: exercise content, helpline numbers, crisis wording, privacy and consent notices, and translations. Mark it `NEEDS_HUMAN_REVIEW` in the code or content and list it in `docs/review-needed.md`. Placeholder content must not be reachable in a production build.

## Session routine

Start of every session:
1. Read `CLAUDE.md` and `docs/decisions.md`.
2. Run the test suite and report the current state: what passes, what fails, what phase we are in.
3. Do not start new work until that is done. Never start a phase while a test from an earlier phase is failing.

End of every session:
1. Run the full test suite, lint and type-check.
2. Update `docs/decisions.md` and `docs/progress.md` with what changed, what is unfinished, and any assumptions made.
3. List anything that needs human review in `docs/review-needed.md`.
