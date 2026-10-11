# Decisions

The locked decisions for this project, each with a short rationale and the date it was recorded. `README.md` Part A is the source. Change a decision here first, then mirror it in `CLAUDE.md`.

When something is ambiguous during the build, the safer and more private option is chosen and added to "Build-time decisions" below.

## Locked decisions

| # | Topic | Decision | Rationale | Date |
|---|---|---|---|---|
| D1 | Age policy | 18+ only for the prototype. Age confirmation at registration. No minors' data collected. | Children's data under India's DPDP Rules may need verifiable guardian consent; excluding minors avoids that until a lawyer has reviewed it. | 2026-10-12 |
| D2 | Authentication | Django session cookies + CSRF. Same site or sibling subdomains, `SameSite=Lax`, `Secure`, `HttpOnly`. No JWT in `localStorage`. Strict CORS allowlist. | An `HttpOnly` cookie cannot be read by injected script, so a cross-site scripting bug cannot steal the session the way it could steal a stored token. | 2026-10-12 |
| D3 | Weekly contact email content | Only display name, week covered, "checked in X of 7 days", and one fixed neutral line. Student previews and confirms before the first send; can pause or revoke at any time. | The email shows that the student is using the app and nothing about how they feel, so it cannot expose mood, notes or any inferred risk. | 2026-10-12 |
| D4 | Check-in free-text notes | Omitted in the MVP. Structured fields only (mood, sleep, energy, stress). | Free text is the most sensitive and hardest data to protect; not collecting it removes the risk entirely. | 2026-10-12 |
| D5 | Deletion vs audit retention | On deletion, all user content is deleted or queued for deletion. Audit and consent events are pseudonymized (one-way hash, no message bodies), kept 12 months, then purged. | Honors the right to deletion while keeping enough evidence to show that consent was handled properly. | 2026-10-12 |
| D6 | Trusted-contact flow | Double opt-in. Unsubscribe link in every email. Rate limits on adding contacts and on SOS sends. | A contact must agree before receiving anything, which prevents the app being used to send unwanted email to a third party. | 2026-10-12 |
| D7 | Offline safety | Safety plan and verified helplines available offline through a PWA service worker. Required. | The moment someone needs support is often the moment the connection is poor. | 2026-10-12 |
| D8 | Automated risk detection | Out of scope. No automatic alerts. Crisis-like chat content triggers a fixed, non-AI response with the user's own safety plan and verified resources. | A classifier will be wrong in both directions, and alerting people without a staffed human response process is unsafe and a breach of trust. | 2026-10-12 |
| D9 | MVP cut line | Phases 1 to 3 and their frontend first. Chat (Phase 4) and Indian-language content afterwards. i18n foundation from the start. | The core loop and its safety boundaries must work before an AI feature is layered on top. | 2026-10-12 |
| D10 | Free text to providers | Never sent to analytics or error tracking. Chat content goes to the AI provider only, with minimal context. Transcripts off by default. | Each third party that receives student text is another place it can leak or be retained. | 2026-10-12 |
| D11 | Languages | English first. `next-intl` so other languages are added by translation files only. Fluent-speaker review before release. | Wellbeing wording that is mistranslated can mislead or harm, so machine translation is never shipped as final. | 2026-10-12 |

## Build-time decisions

Choices made while building where the specification was silent or contradictory.

| # | Topic | Decision | Rationale | Date |
|---|---|---|---|---|
| B1 | Check-in "optional note" in blueprint section 3 and section 6 | Not built. D4 applies. | Part A overrides Part E for decisions. | 2026-10-12 |
| B2 | Blueprint API lists `DELETE /api/v1/sharing/consent/{id}` | Revoking sets `status=revoked` and `revoked_at`; the row is kept. | Consent history must stay visible to the student (non-negotiable 2, README C.6). | 2026-10-12 |
| B3 | Product name | The repository folder name `mirrorspace` is treated as a working name only. User-facing copy uses a single configurable app-name string. | No name was specified; a single string keeps renaming cheap. | 2026-10-12 |
| B4 | Registering with an email that already has an account | The API gives the same 201 reply either way. No second account is made; the real owner gets an email saying someone tried. Resend-verification and password-reset replies are equally uniform. | Having an account in a wellbeing app is itself sensitive, so nobody should be able to test whether a given person uses it. | 2026-10-12 |
| B5 | Accounts that never confirm their email | Deleted automatically after 7 days (`UNVERIFIED_ACCOUNT_TTL_DAYS`). | Data minimization: an address typed by mistake, or by someone else, is not kept. | 2026-10-12 |
| B6 | Tokens in emailed links | Carried in the URL fragment (`#token=...`), not the query string. | Browsers never send the fragment to a server, so tokens stay out of access logs and Referer headers. | 2026-10-12 |
| B7 | Session lifetime | Idle timeout of 7 days, renewed on each request (`SESSION_COOKIE_AGE_SECONDS`). | Short enough to limit exposure on a shared or lost phone, long enough not to lock out a weekly user. | 2026-10-12 |
| B8 | Account deletion | Requires the current password. The account is locked and every session ended immediately; a background task erases the data, and an hourly sweep completes any erase whose task was lost. | Deletion is irreversible, so it needs proof of identity; and it must take effect even if the queue is down. | 2026-10-12 |
| B9 | Sign-in before email confirmation | Not allowed. Completing a password reset also confirms the email. | Stops someone registering with another person's address and using the account. | 2026-10-12 |
| B10 | OpenAPI schema in production | Staff only. Public in local and test. | The route list is useful to the team and of no use to students. | 2026-10-12 |
| B11 | Django admin | Shows that an account exists and can lock it. Profiles and wellbeing data are not registered. | Operators should not be able to browse student records (blueprint section 2). | 2026-10-12 |
| B12 | Unauthenticated requests | Answered with 401, not DRF's default 403. | Lets the frontend tell "signed out" from "not allowed" without guessing. | 2026-10-12 |
| B13 | Free text in Phase 2 | Two short fields only: a trigger's `label` (80 characters) and an episode's `what_helped` (200). Both are encrypted at rest with Fernet (`FIELD_ENCRYPTION_KEYS`), never logged, and excluded from any email. The blueprint's optional episode "description" is not built. | The features need the person's own words, but long open text is the hardest data to protect, so it is kept short and encrypted (same reasoning as D4). | 2026-10-12 |
| B14 | Scales | Mood, sleep quality, energy, stress and episode intensity all use 1 to 5. Sleep duration is hours with one decimal. | One scale everywhere keeps the check-in under 20 seconds and the controls large. | 2026-10-12 |
| B15 | Second check-in on the same day | `POST /check-ins` replaces that day's check-in (200) instead of failing. | No error state on a flaky phone connection, and still exactly one row per day. | 2026-10-12 |
| B16 | Back-dating check-ins | Allowed up to 7 days back, never forward. The date cannot be changed afterwards. | Lets someone fill in yesterday without making history freely editable. | 2026-10-12 |
| B17 | Which local date a check-in gets | The date in the person's time zone at the moment of saving, using the zone database (daylight saving aware). Changing time zone later does not rewrite past check-ins. | A late-night check-in belongs to the day the person was living in. | 2026-10-12 |
| B18 | Unreviewed content | Hidden from the API unless `SHOW_UNREVIEWED_CONTENT` is on; production settings force it off. When shown, items carry `reviewed: false`. Draft and retired content is never served. | Non-negotiable 8: placeholders must not be able to reach students. | 2026-10-12 |
| B19 | Pattern observations | Shown only with 6+ paired days, 2+ days on each side of the person's median sleep, and a difference of 0.5 or more. Otherwise a neutral "not enough yet" line. | Avoids reading meaning into noise. | 2026-10-12 |
| B20 | Exercise feedback | An append-only event log per user; "hidden" is derived from the latest hide/unhide event. Events can be deleted, not edited. | Simple, reversible, and fully exportable. | 2026-10-12 |

## Open questions

These are for the project owner. Until answered, the stated default is used.

| # | Question | Default until answered |
|---|---|---|
| Q1 | Which transactional email provider (Resend, Postmark, other)? | Provider-agnostic adapter; console backend locally; no provider SDK is hard-wired. |
| Q2 | Which hosted LLM provider and model for Phase 4? | Provider adapter with a mocked implementation in tests; key read from environment only. |
| Q3 | Where will the API, worker, database and Redis be hosted? | Generic Docker host with managed PostgreSQL and Redis; frontend deployable to Vercel or as a container. |
| Q4 | Exact wording of the fixed neutral line in the weekly email. | README example: "This is a routine weekly note. Silence does not mean anything either way." Marked NEEDS_HUMAN_REVIEW. |
| Q5 | Default timezone for new accounts. | Browser-detected timezone sent at registration, falling back to `Asia/Kolkata`. |
| Q6 | Chat transcript retention period when a student turns transcripts on. | 30 days, user-adjustable downward, deletable at any time. |
| Q7 | Who is the named human owner for helpline verification, and how often? | Unassigned. Entries older than 90 days are flagged stale; release is blocked on re-verification. |
| Q9 | Should the patterns screen show the "You checked in on X of the last N days" line at all? | Shown, as a plain count with no judgement. Flagged for review under R10. |
| Q8 | Final product name and sender domain for email. | Working name only; sender address comes from environment. |
