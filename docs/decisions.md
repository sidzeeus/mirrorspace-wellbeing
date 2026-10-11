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
| Q8 | Final product name and sender domain for email. | Working name only; sender address comes from environment. |
