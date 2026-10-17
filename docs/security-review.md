# Security review

Hardening pass over the whole repository (spec Prompt 8), carried out on 2026-10-12 against the blueprint's security baseline (Part E, section 8).

> This is an engineer's self-review with automated checks. It is not a penetration test or an independent audit. Both are recommended before real students use the app.

## Summary

| Severity | Open | Notes |
|---|---|---|
| High | 0 | |
| Medium | 4 | S1 to S4 below. None exposes student records by itself. |
| Low | 5 | S5 to S9 below. |

Automated evidence: 766 backend tests and 66 browser tests pass; `pip-audit` and `npm audit --omit=dev` report no known vulnerabilities; `manage.py check --deploy` passes under production settings with no warnings.

## Baseline checklist

| Item | Status | Evidence |
|---|---|---|
| HTTPS everywhere | Pass (configured) | `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS in `backend/config/settings/production.py`; `TestSecuritySettings::test_production_settings_are_locked_down` |
| HSTS | Pass, starts low | 3600 seconds by default; raise to a year after HTTPS is confirmed on every hostname (runbook). Preload is opt-in. |
| Secure cookies | Pass | `Secure`, `HttpOnly`, `SameSite=Lax` on session and CSRF cookies; `TestLogin::test_session_cookie_flags` |
| CSRF | Pass | Enforced on every write, signed in or not; `tests/test_routes.py::test_protected_writes_need_a_csrf_token`, `test_public_writes_need_a_csrf_token_too`. Two documented exceptions: one-click unsubscribe (signed token) and the provider webhook (shared secret). |
| CORS | Pass | Allowlist only, never a wildcard; `TestApiDefaults::test_cors_allows_only_the_frontend_origin`. The browser normally uses the same-origin proxy, so CORS is a second line. |
| `SECRET_KEY` and key handling | Pass | Required from the environment in production with no default; `test_refuses_to_start_without_required_variables` covers `DJANGO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `FIELD_ENCRYPTION_KEYS`, `PSEUDONYM_KEY`. The AI key is read by the SDK from `ANTHROPIC_API_KEY`, never by settings. No secret is in the repository or in an image layer. |
| `DEBUG` off | Pass | `production.py`; asserted in tests |
| `ALLOWED_HOSTS` | Pass | Required in production |
| Secure proxy headers | Pass | `SECURE_PROXY_SSL_HEADER`; `NUM_PROXIES` for the real client address |
| `check --deploy` | Pass | `TestProductionSettings::test_deploy_check_passes_with_no_warnings` |
| Admin restrictions | Partial | Staff only, configurable URL, and no student record is registered (`test_admin_exposes_no_student_records`). No MFA: see S1. |
| Rate limits | Pass at the application | Per-route limits on sign-in, registration, email-sending actions, export, contacts, SOS, public token links and chat. Infrastructure-level limiting: see S2. |
| Request-size limits | Pass | 256 KB body limit, JSON only; `test_request_bodies_are_size_limited` |
| Dependency audit | Pass | `pip-audit -r requirements.txt` and `npm audit --omit=dev`, both in CI |
| Password storage | Pass | Argon2; minimum length 10; common-password check |
| Field encryption | Pass | Fernet for all free text; key rotation tested (`TestFieldEncryption`) |

## Every route, enumerated

`backend/tests/test_routes.py` walks the URL configuration, so a route added later is checked without anyone writing a new test.

| Check | Result |
|---|---|
| Every route is either on the explicit public list (20 routes, each with a reason) or answers 401 without sign-in | Pass, for every method of every route |
| No view is public by accident: the views that declare `AllowAny` are exactly the public list | Pass |
| Every viewset over a model with a `user` field is built on `OwnedModelViewSet` | Pass |
| Every owned collection has a cross-user contract test | Pass: check-ins, episodes, triggers, exercise events, trusted contacts, consents, notifications, chat sessions, chat feedback; and the safety plan |
| Signed-in routes that are not owned collections take no id in the URL | Pass |
| Unknown and malformed ids answer 404, never 500 | Pass |
| API responses carry `Cache-Control: no-store` | Pass (`config/middleware.py`) |

## Retention, deletion and export

| Check | Result | Evidence |
|---|---|---|
| Deleting an account removes every row it owns | Pass | `tests/test_data_coverage.py::TestDeletion`, by introspection over every model linked to a user |
| The only data that outlives an account is on a documented exception list | Pass | `SURVIVES_DELETION` contains `AuditEvent` only |
| Audit events are pseudonymized, not linked | Pass | `test_audit_trail_is_pseudonymized_not_linked` |
| Audit events are purged after 12 months | Pass | `test_events_are_purged_after_the_retention_period`; scheduled daily |
| The export contains every user-owned model | Pass | `test_every_user_owned_model_is_in_the_export` |
| Deletion still takes effect if the queue is down | Pass | `TestDeletionWhenTheQueueIsDown` |
| Live check on the Docker stack | Pass | After deleting an account: zero owned rows, audit rows pseudonymized |

## Logs, queue and error tracking

Canary-string tests plant a recognizable string and assert it never appears.

| Where | Result | Evidence |
|---|---|---|
| Application logs: account flows, triggers and episodes, safety plan, contacts and messages, chat prompts and replies | Pass | `tests/test_observability.py`, and a canary test in each app |
| Task names and arguments | Pass | `TestBackgroundTasks`: names are generic, every task takes at most a `user_id` or `notification_id`, results are not stored |
| Audit trail | Pass | No free-text column; metadata keys are allow-listed |
| Sentry | Pass (by unit test) | `scrub_sentry_event` strips bodies, cookies, headers, user, extras, breadcrumbs and frame variables. Not verified against a real Sentry project: see S6. |
| Analytics | Not applicable | There is no analytics library in the product. |
| Live check | Pass | Structured logs from a full sharing and SOS run contained none of the planted names, addresses or message text. |

In local development only, the worker prints emails to its console so a developer can read the confirmation link. Production does not use that email backend.

## Load and resilience

| Check | Result |
|---|---|
| List endpoints run a bounded number of queries with 30 rows each | Pass, 14 queries or fewer on nine endpoints (`TestQueryCounts`) |
| Export of a busy account | Pass, 40 queries or fewer |
| Planning 200 due weekly notes | Pass: 200 planned once each, a second run plans none |
| Sending those 200 with every task delivered twice | Pass: 200 emails, 200 duplicates skipped |
| Live response times, local Docker, development server, 8 concurrent requests | Health p95 29 ms, readiness p95 115 ms, signed-in reads p95 240 to 380 ms |
| Backup and restore rehearsal | Pass: `infra/backup-restore-rehearsal.sh` restored a real dump into a scratch database, matched row counts across 32 tables, and read encrypted fields with the application keys |

The response times are from a laptop and the development server. They show that nothing is pathologically slow, not what production will do. One real finding came out of the run and was fixed (F5 below).

## Findings fixed during this pass

| # | Finding | Fix |
|---|---|---|
| F1 | A trusted contact's email address could be changed with `PATCH`, skipping double opt-in for the new address. | The address is read-only after creation (`TrustedContactUpdateSerializer`). Caught by a test in Phase 3. |
| F2 | The handler that reschedules the weekly note after a time-zone change was held by a weak reference and silently disconnected. | Connected with `weak=False`. Caught by a test. |
| F3 | API responses had no caching directive when the API was called directly rather than through the frontend proxy. | `NoStoreApiMiddleware` adds `Cache-Control: no-store`. |
| F4 | The frontend sent no Content-Security-Policy. | A partial policy now blocks framing, plugins, foreign form targets and `<base>` changes. Script restrictions remain open (S3). |
| F5 | Under a burst of requests the development server answered the readiness probe with 503: persistent database connections accumulated, one per request thread. | Persistent connections are off in local settings. Production's worker processes are unaffected. |
| F6 | The full-screen exercise player rendered underneath the navigation bar. | Rendered into the page body. Caught by a browser test. |
| F7 | The saved safety plan could not be opened offline on the Plan screen. | The signed-in screens render from device copies when there is no connection. Caught by a browser test. |

## Open findings

| # | Severity | Finding | Recommendation |
|---|---|---|---|
| S1 | Medium | The Django admin has no multi-factor authentication. Its exposure is limited (it shows that accounts exist, and manages reviewed content; no student record is registered), but a stolen staff password could lock accounts or change exercise, helpline and chat content. | Add TOTP for staff (for example `django-otp`), or put the admin behind the host's identity-aware proxy or a VPN. Until then, keep the number of staff accounts minimal and the admin URL unguessable. |
| S2 | Medium | Rate limiting exists only in the application. A flood of requests still reaches Django before being refused. | Add rate limiting and bot protection at the edge (the host's load balancer or a CDN). The blueprint notes that application throttling is not a substitute. |
| S3 | Medium | The Content-Security-Policy does not restrict scripts. The app has no known injection point (React escapes output; the only `dangerouslySetInnerHTML` is a constant boot script), but a script policy would limit the damage of one. | Add a nonce-based `script-src` through Next.js middleware, then test every screen. |
| S4 | Medium | No real email or AI provider has been connected. Delivery, bounce handling and the chat adapter are tested against fakes. | Before launch: connect the chosen providers in a staging environment, send real mail, trigger a real bounce, run the chat evaluation set against the real model, and review both providers' data terms (review-needed R13, R22, R24). |
| S5 | Low | `NUM_PROXIES` must match the real number of proxies in front of the API (the frontend proxy plus the host's load balancer), or per-address limits will count the wrong address. | Set it per environment and verify with a request from a known address (runbook). |
| S6 | Low | Sentry scrubbing is unit-tested but has not been checked against a live Sentry project. | In staging, raise a test error containing a canary string and confirm the event is clean. Also turn on Sentry's own server-side scrubbing. |
| S7 | Low | Two secrets must never be lost or changed: `FIELD_ENCRYPTION_KEYS` (loss makes encrypted fields unreadable) and `PSEUDONYM_KEY` (a change stops the do-not-email list matching). | Store both in the secret manager with versioning and back them up separately from the database (review-needed R18). |
| S8 | Low | A session stays valid for 7 idle days and there is no "sign out everywhere" button. Changing the password or deleting the account does end every session. | Consider a shorter idle time for shared devices, and a sign-out-everywhere action. |
| S9 | Low | The service worker caches the app's page shells. They contain no personal data, but a compromised release would persist until the next update is accepted. | Keep the update prompt; bump the cache version on every release (it is one constant in `frontend/public/sw.js`). |

## Left for human review

Nothing here is a code defect, but each blocks real use. Full list in `docs/review-needed.md`.

- An independent security test and a safeguarding review of the whole product (R14).
- The crisis phrase list and fixed replies, with measured false positives and negatives (R3).
- All clinical, legal and safety wording, and every translation (R1, R4 to R6, R9 to R12, R15, R19).
- Helpline numbers, verified by a named owner before each release (R2).
- Provider data-processing terms (R13) and the key-handling procedure (R18).
