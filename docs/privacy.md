# Privacy: what the app holds, shares, keeps and deletes

> **NEEDS_HUMAN_REVIEW.** This is an engineering description of how the software behaves today. It is not a privacy notice and not legal advice. Before any real student uses the app, an India-qualified privacy lawyer must review it against the DPDP Act and Rules, and the student-facing notices must be written from it (docs/review-needed.md R6, R7, R8, R13).

This file is updated with every phase. It describes Phases 1 to 3.

## Principles the code enforces

| Principle | How it is enforced | Proof |
|---|---|---|
| Collect little | Check-ins have no free-text note. Free text exists in four places only: trigger names, "what helped", the safety plan, and a trusted contact's details. | `apps/checkins/tests/test_checkins.py::test_there_is_no_free_text_note` |
| One person's data is theirs alone | Every query for user-owned rows is filtered by the signed-in user. Another person's id answers "not found". | `tests/harness.py`, applied to every user-owned endpoint |
| Sharing is off until switched on | No consent row, no schedule and no email exist until the student explicitly creates them. | `apps/sharing/tests/test_consent.py::TestSharingIsOffByDefault` |
| Nobody is emailed without agreeing | A trusted contact gets one invitation and nothing more until they accept it themselves. | `apps/sharing/tests/test_contacts.py::TestDoubleOptIn` |
| Nothing is sent automatically | No classifier, score or schedule can send a Support (SOS) message. | `apps/sharing/tests/test_sos.py::TestNeverAutomatic`, `test_only_the_sos_module_can_create_an_sos_message` |
| Sensitive text stays out of logs | Logs carry ids and event names. A redaction filter is the safety net. | canary-string tests in `tests/test_observability.py` and each app |

## What is stored

| Data | Where | Protection |
|---|---|---|
| Email, password hash (Argon2), language | `accounts_user` | Password is never stored or logged in readable form. |
| Display name, time zone | `accounts_profile` | Owner only. |
| Check-ins: mood, sleep hours and quality, energy, stress, local date | `checkins_checkin` | Owner only. Numbers only. |
| Trigger names; episodes with intensity, duration and "what helped" | `episodes_*` | Trigger name and "what helped" are **encrypted at rest**. |
| Exercise feedback (completed, helpful, not helpful, hidden) | `wellbeing_exerciseevent` | Owner only. |
| Safety plan: warning signs, steps, people, chosen helplines | `safety_safetyplan` | All text **encrypted at rest**. No admin view. Never shared or sent. |
| Trusted contacts: name, email, relationship, status | `sharing_trustedcontact` | Name, email, relationship **encrypted at rest**. A keyed fingerprint of the email is kept for duplicate and do-not-email checks. |
| Consents: purpose, fields agreed, notice version, dates, schedule | `sharing_consentrecord` | Kept as the student's own history until the account is deleted. |
| Notifications: purpose, status, dates, provider reference | `notifications_notification` | No message body is kept. An SOS message's approved text is held encrypted only until it is sent. |
| Do-not-email list | `sharing_suppressedaddress` | Keyed fingerprints only. It contains no addresses. |
| Audit events: action, object type, codes | `audit_auditevent` | No message bodies, names or addresses. See retention below. |
| Sign-in sessions | `django_session` | `HttpOnly`, `Secure`, `SameSite=Lax` cookie; 7-day idle timeout. |

Not stored at all: free-text notes on check-ins, location, device identifiers, contacts lists, analytics or advertising identifiers, any assessment or risk label about a student.

### Encryption

- **In transit:** HTTPS is required in production (redirect, HSTS, secure cookies).
- **At rest, per field:** the free text listed above is encrypted with Fernet before it reaches the database, using `FIELD_ENCRYPTION_KEYS`. A database dump or backup does not reveal it. The first key encrypts and every listed key decrypts, so keys can be rotated.
- **At rest, whole database:** expected from the managed PostgreSQL provider (to be confirmed at deployment).
- **Fingerprints:** a contact's email in the do-not-email list and a deleted user's id in the audit trail are stored as HMAC-SHA256 values keyed with `PSEUDONYM_KEY`. They cannot be reversed or recomputed without that secret.

## What can leave the system, and only when

### 1. Invitation to a trusted contact
Sent once when the student adds a contact. Contains the student's display name, a description of what the contact might receive, and an accept/decline link. The student may re-send it at most twice more, at least 24 hours apart. If the contact does nothing, nothing else is ever sent.

### 2. Weekly note (off by default)
Sent only when **all** of these are true at the moment of sending:

1. The student turned it on for that contact, after being shown the notice and the exact message, and sent an explicit confirmation.
2. The contact accepted the invitation.
3. The consent is active (not paused, not withdrawn).
4. The student confirmed it within the last 90 days. Otherwise it pauses itself.
5. The address is not on the do-not-email list.

The note contains exactly four things:

| Field | Example |
|---|---|
| Display name | Asha Rao |
| Week covered | 11 May 2026 to 17 May 2026 |
| Days checked in | checked in 3 of 7 days |
| One fixed line | This is a routine weekly note. Silence does not mean anything either way. |

It never contains mood, sleep, energy or stress values, episodes, triggers, "what helped", the safety plan, chats, or any judgement about how the student is. This is enforced by structure: the renderer accepts one small object with exactly those fields (`apps/sharing/weekly.py`), and tests compare the sent email byte for byte with one built from those four values alone (`apps/sharing/tests/test_weekly_message.py`).

### 3. Support (SOS) message
Sent only when the student, in that moment, chooses a contact, is shown the exact recipient and exact text, and confirms. The text is fixed; the student cannot type into it. Limits: 3 an hour and 6 a day. The app reports only that the message was queued. It never claims the message was delivered or read.

### 4. Account emails
Email confirmation, password reset and "you already have an account" go to the student's own address only.

### Processors

| Processor | Receives | Status |
|---|---|---|
| Email provider | Recipient address, subject and body of the emails above | Not chosen yet (decisions.md Q1). Its retention and data-use terms need review (R13). |
| Error tracking (Sentry), if enabled | Error type, code location, request method and path | Request bodies, cookies, headers, user details and local variables are stripped before sending. Off unless `SENTRY_DSN` is set. |
| AI provider | Nothing yet | Phase 4. |

Nothing is sent to analytics or advertising services. There are none in the product.

## What a trusted contact can do

A contact has no account and cannot see any student record. From any email they can unsubscribe with one click (a link in the message and a standard `List-Unsubscribe` header). That immediately withdraws every consent involving them. They can also choose to block every message from this app to their address; the address is then stored only as a fingerprint on the do-not-email list.

A permanently bouncing address, or a spam complaint reported by the email provider, has the same effect automatically.

## What the student controls

| Action | Route |
|---|---|
| See every consent ever given, with version and dates | `GET /api/v1/sharing/consent` |
| Preview the exact weekly note | `GET /api/v1/sharing/preview` |
| Pause, resume, confirm, or withdraw | `POST .../pause`, `.../resume`, `.../confirm`, `DELETE /api/v1/sharing/consent/{id}` |
| See what was sent on their behalf and its status | `GET /api/v1/notifications` |
| Remove a contact (also withdraws consent) | `DELETE /api/v1/trusted-contacts/{id}` |
| Download everything held about them | `GET /api/v1/export` |
| Delete the account | `DELETE /api/v1/account` |

## Retention and deletion

| Data | Kept until |
|---|---|
| Everything a student owns | The student deletes it, or deletes the account. |
| An account that never confirmed its email | 7 days, then removed automatically. |
| An SOS message's approved text | It is sent, cancelled or fails. Then it is blanked. |
| Expired sign-in sessions | Cleared nightly. |
| Audit events | 12 months from the event, then purged (`AUDIT_RETENTION_DAYS`). |
| Do-not-email fingerprints | Indefinitely, so a person who asked not to be emailed stays un-emailed. They identify no one without the server secret. |

### When an account is deleted

1. The current password is required.
2. The account is locked and every session ends immediately.
3. A background task erases the account. If that task is lost, an hourly sweep completes it.
4. Deleted by database cascade: profile, check-ins, triggers, episodes, exercise feedback, safety plan, trusted contacts, consents, notifications.
5. **Not deleted, by decision D5:** audit events. Before the account goes, each event's link to the user is cut and replaced with a one-way fingerprint, and object ids are blanked. What remains is, for example, "a pseudonymous account granted weekly_summary consent under notice version X on this date". These are purged 12 months after they were recorded.

A test discovers every table linked to a user by introspection and fails if one is neither deleted with the account nor on the explicit, documented exception list (`tests/test_data_coverage.py`). The same test fails if a table is missing from the export.

## Open items for the reviewer

- Whether the 18+ self-confirmation is sufficient (R7).
- Whether keeping pseudonymized audit events for 12 months, and do-not-email fingerprints indefinitely, is acceptable and how the notice should describe it (R8).
- The wording of every notice and email (R4, R5, R6, R15).
- The email provider's terms (R13).
- Whether trusted contacts, whose name and email are stored on the student's say-so, need their own notice beyond the invitation email.
