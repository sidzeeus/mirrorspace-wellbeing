# API reference

Base path: `/api/v1`. The machine-readable description is at `GET /api/v1/schema` (OpenAPI 3; staff only in production).

This file documents the routes that exist today (Phases 1 to 4). It is updated with each phase.

## Rules that apply to every route

| Rule | Detail |
|---|---|
| Format | JSON in, JSON out. Other content types are rejected. Bodies over 256 KB are rejected. |
| Authentication | Session cookie. Every route needs a signed-in user unless marked **public**. |
| CSRF | Every `POST`, `PUT`, `PATCH`, `DELETE` needs the header `X-CSRFToken`. Get the token from `GET /auth/csrf`. |
| Ownership | A user only ever reaches their own rows. Someone else's id answers `404`, exactly like an id that does not exist. The owner is always taken from the session; a `user` field in the body is ignored. |
| Paths | No trailing slash. Ids are UUIDs. |
| Pagination | List routes return `{"count", "next", "previous", "results"}`, 20 per page. `?page=2`, `?page_size=` up to 100. |
| Rate limits | 60 requests a minute signed out, 240 signed in, plus tighter limits noted per route. Over the limit: `429` with a `Retry-After` header. |

### Common errors

| Status | When | Body |
|---|---|---|
| 400 | A field is invalid | `{"field_name": ["What is wrong and how to fix it."]}`. Errors not tied to one field use `non_field_errors`. Some routes add `{"detail", "code"}`. |
| 401 | Not signed in, or the session expired | `{"detail": "Authentication credentials were not provided."}` |
| 403 | CSRF token missing or wrong | `{"detail": "Security check failed. Reload the page and try again.", "code": "csrf_failed"}` |
| 404 | No such row, or it belongs to someone else | `{"detail": "No ... matches the given query."}` |
| 405 | Method not supported on this route | `{"detail": "Method \"PATCH\" not allowed."}` |
| 429 | Too many requests | `{"detail": "Request was throttled. Expected available in 42 seconds."}` |

## Platform

### GET /health (public)
Is the process up? Does not touch the database. Not rate limited.

```json
{"status": "ok"}
```

### GET /ready (public)
Are the database and Redis reachable? `200` when both are, otherwise `503`. Names components only.

```json
{"status": "ok", "checks": {"database": true, "cache": true}}
```

### GET /schema
OpenAPI document. Public locally, staff only in production.

## Accounts

### GET /auth/csrf (public)
Sets the CSRF cookie and returns the token to send back as `X-CSRFToken`.

```json
{"csrf_token": "p9K...long-random-value"}
```

### POST /auth/register (public)
Limit: 5 an hour per address.

```json
{
  "email": "asha@example.com",
  "password": "a-long-passphrase",
  "age_confirmed": true,
  "preferred_language": "en",
  "timezone": "Asia/Kolkata",
  "display_name": "Asha"
}
```

Only `email`, `password` and `age_confirmed` are required. `201`:

```json
{"detail": "If that address can be used, we have sent an email to it. Check your inbox."}
```

The reply is identical whether or not the address already has an account, so the route cannot be used to find out who uses the app. The person is not signed in until they confirm their email.

Errors (`400`): `age_confirmed` not `true`; password shorter than 10 characters, entirely numeric, too common or too similar to the email; unknown `timezone` or `preferred_language`; malformed `email`.

### POST /auth/verify-email (public)

```json
{"token": "value-from-the-emailed-link"}
```

`200` `{"detail": "Your email is confirmed. You can sign in now."}`. Using the link twice is harmless.
`400` `{"detail": "This link is not valid or has expired. Request a new one.", "code": "invalid_link"}`. Links last 3 days.

### POST /auth/resend-verification (public)
Limit: 5 an hour per address. Body `{"email": "..."}`. Always `200` with the same message as registration.

### POST /auth/login (public)
Limits: 5 a minute per address, 10 an hour per account.

```json
{"email": "asha@example.com", "password": "a-long-passphrase"}
```

`200` returns the account (same shape as `GET /auth/me`) and sets the session cookie.

| Status | `code` | Meaning |
|---|---|---|
| 400 | `invalid_credentials` | Wrong email or password. Unknown, wrong and deactivated accounts all look the same. |
| 403 | `email_not_verified` | Correct password, but the email is not confirmed yet. |
| 429 | | Too many attempts. |

### POST /auth/logout
`204`, no body. The server-side session is removed.

### GET /auth/me

```json
{
  "id": "53faac08-210b-40ae-8b56-881a71966334",
  "email": "asha@example.com",
  "email_verified": true,
  "preferred_language": "en",
  "display_name": "Asha",
  "timezone": "Asia/Kolkata",
  "created_at": "2026-10-12T03:37:09.579048Z"
}
```

### PATCH /auth/me
Changes `preferred_language`, `display_name` (up to 60 characters) or `timezone`. Any other field is ignored; the email cannot be changed here. Returns the updated account. `400` for an unknown time zone or language.

### POST /auth/password-reset (public)
Limit: 5 an hour per address. Body `{"email": "..."}`. Always `200` with the generic message.

### POST /auth/password-reset/confirm (public)

```json
{"uid": "from-the-link", "token": "from-the-link", "new_password": "a-new-long-passphrase"}
```

`200` `{"detail": "Your password has been changed. Sign in with the new one."}`. Every existing session stops working. The link lasts 1 hour and works once.
`400` with `code: "invalid_link"`, or `{"new_password": [...]}` if the password is too weak (the link stays usable).

### DELETE /account
Limit: 5 an hour. Body `{"password": "current-password"}`.

`202`:

```json
{"detail": "Your account is locked and is being deleted. You have been signed out."}
```

The account is locked and all sessions end immediately. A background task then erases the account and every row it owns.
`400` `{"detail": "That password is incorrect. Your account has not been deleted.", "code": "invalid_password"}`.

### GET /export
Limit: 10 an hour. Returns everything held about the signed-in person as a JSON download (`Content-Disposition: attachment`, `Cache-Control: no-store`).

```json
{
  "format_version": 1,
  "exported_at": "2026-10-12T04:10:00.000000+00:00",
  "account": {"id": "...", "email": "asha@example.com", "preferred_language": "en", "display_name": "Asha", "timezone": "Asia/Kolkata", "created_at": "...", "email_verified_at": "...", "age_confirmed_at": "..."},
  "check_ins": [{"id": "...", "local_date": "2026-10-11", "timezone": "Asia/Kolkata", "mood": 4.0, "sleep_hours": 6.5, "sleep_quality": null, "energy": 3.0, "stress": null, "created_at": "...", "updated_at": "..."}],
  "triggers": [{"id": "...", "label": "Exam week", "is_active": true, "preferred_exercises": ["five-senses"], "created_at": "..."}],
  "episodes": [{"id": "...", "occurred_at": "...", "intensity": 4, "duration_minutes": 20, "trigger_id": "...", "helped_exercise": "five-senses", "what_helped": "Calling my sister", "created_at": "..."}],
  "exercise_events": [{"id": "...", "exercise": "five-senses", "kind": "not_helpful", "created_at": "..."}],
  "safety_plan": {"warning_signs": ["..."], "coping_steps": ["..."], "people": ["..."], "resources": ["in-tele-manas"], "updated_at": "..."},
  "trusted_contacts": [{"id": "...", "name": "Meera", "email": "meera@example.com", "relationship": "sister", "status": "confirmed", "invited_at": "...", "responded_at": "...", "created_at": "..."}],
  "consents": [{"id": "...", "purpose": "weekly_summary", "contact_id": "...", "scope": ["display_name", "week_start", "week_end", "check_in_days"], "notice_version": "2026-10-placeholder-1", "status": "revoked", "status_reason": "revoked_by_user", "granted_at": "...", "last_confirmed_at": "...", "paused_at": null, "revoked_at": "...", "send_weekday": 0, "send_hour": 9}],
  "notifications": [{"id": "...", "purpose": "weekly_summary", "contact_id": "...", "status": "sent", "status_code": "", "scheduled_at": "...", "sent_at": "..."}],
  "audit_events": [{"action": "consent.granted", "object_type": "consentrecord", "metadata": {"purpose": "weekly_summary", "notice_version": "2026-10-placeholder-1"}, "created_at": "..."}]
}
```

## Check-ins

One optional check-in per person per local day. There is no free-text note. Every value is optional, but at least one must be given: skipping saves nothing.

| Field | Type | Notes |
|---|---|---|
| `mood`, `sleep_quality`, `energy`, `stress` | integer 1 to 5, or null | |
| `sleep_hours` | decimal 0 to 24, one decimal place, or null | |
| `local_date` | date | Optional on create. Defaults to today in the person's time zone. May be up to 7 days back, never in the future. Cannot be changed later. |
| `timezone` | string | Read only. The zone used to work out `local_date`. |

### GET /check-ins
Newest first. Filters: `?from=2026-10-01&to=2026-10-31`.

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "0b6c1f0e-6a1a-4f0c-9d0e-0f6a5e2f9a11",
      "local_date": "2026-10-12",
      "timezone": "Asia/Kolkata",
      "mood": 4,
      "sleep_hours": "7.5",
      "sleep_quality": 3,
      "energy": 2,
      "stress": null,
      "created_at": "2026-10-12T04:02:11.120000Z",
      "updated_at": "2026-10-12T04:02:11.120000Z"
    }
  ]
}
```

### POST /check-ins

```json
{"mood": 4, "sleep_hours": "7.5", "sleep_quality": 3, "energy": 2}
```

`201` when the day is new. `200` when that day already had a check-in: the new values replace the old ones, and values left out become empty. Both return the saved check-in.

Errors (`400`):
- `{"mood": ["Ensure this value is less than or equal to 5."]}` and similar for any out-of-range value.
- `{"non_field_errors": ["Choose at least one value to save, or skip the check-in."]}`
- `{"local_date": ["A check-in cannot be dated in the future."]}`
- `{"local_date": ["A check-in can be added for the last 7 days only."]}`

### GET, PUT, PATCH, DELETE /check-ins/{id}
Read, change or remove one check-in. `PATCH` changes only the fields sent. `DELETE` answers `204`.
`400` `{"local_date": ["The date of a check-in cannot be changed."]}`, or the "at least one value" error if the change would empty it.

## Patterns

### GET /patterns
Descriptive summaries of the person's own check-ins. `?days=` sets the period: 7 to 90, default 28 (values outside are clamped).

```json
{
  "range": {"from": "2026-09-15", "to": "2026-10-12", "days": 28},
  "check_in_days": 9,
  "series": [
    {"local_date": "2026-10-05", "mood": 3.0, "sleep_hours": 5.0, "sleep_quality": null, "energy": 2.0, "stress": 3.0}
  ],
  "weekly": [
    {"week_start": "2026-10-05", "check_ins": 5, "average_mood": 3.2, "average_sleep_hours": 6.4, "average_sleep_quality": null, "average_energy": 2.8, "average_stress": 3.0}
  ],
  "observations": [
    {"code": "check_in_count", "text": "You checked in on 9 of the last 28 days.", "params": {"count": 9, "days": 28}},
    {"code": "sleep_energy_lower", "text": "On days you logged less sleep than your usual, you rated your energy lower on average.", "params": {}}
  ],
  "note": "These observations come only from what you entered. They are not a diagnosis, and they cannot show that one thing leads to another."
}
```

How observations are chosen:
- A sleep comparison appears only when both values exist on at least 6 days, at least 2 days fall on each side of the person's usual (median) sleep, and the two averages differ by at least 0.5.
- When no comparison qualifies, `not_enough_data` is returned instead.
- Observations describe what was entered. They never diagnose, predict, advise or claim a cause. A unit test scans every template for banned wording.
- `code` and `params` let the frontend show its own translated sentence. `text` is the English placeholder, marked NEEDS_HUMAN_REVIEW.

## Triggers

Things a person has noticed tend to come before a hard moment, in their own words. Labels are encrypted at rest.

| Field | Type | Notes |
|---|---|---|
| `label` | string, 1 to 80 characters | Unique per person, ignoring case. |
| `is_active` | boolean | `false` archives the trigger. Archived triggers are kept but not listed. |
| `preferred_exercise_ids` | list of exercise ids | Must be exercises the person can see. |

### GET /triggers
Active triggers, oldest first. `?include_archived=true` adds archived ones.

### POST /triggers

```json
{"label": "Exam week", "preferred_exercise_ids": ["7d0f7d5e-1c1c-4f5e-8c11-2c0c2a8f3b10"]}
```

`201`:

```json
{"id": "c1d6f5a2-4a0b-4a3e-9e0a-9a1a4b9d2e77", "label": "Exam week", "is_active": true, "preferred_exercise_ids": ["7d0f7d5e-1c1c-4f5e-8c11-2c0c2a8f3b10"], "created_at": "2026-10-12T04:05:00.000000Z"}
```

Errors (`400`): blank or over-long `label`; `{"label": ["You already have a trigger with this name."]}`; an exercise id that does not exist or is not reviewed; more than 50 triggers.

### GET, PUT, PATCH, DELETE /triggers/{id}
Archive with `PATCH {"is_active": false}`. `DELETE` removes the trigger; past episodes that used it are kept with no trigger.

## Episodes

A moment the person chose to log. No diagnostic labels and no long description.

| Field | Type | Notes |
|---|---|---|
| `occurred_at` | date-time, required | Not in the future. |
| `intensity` | integer 1 to 5, required | |
| `duration_minutes` | integer 0 to 1440, or null | |
| `trigger` | trigger id or null | Must be one of the person's own triggers. |
| `helped_exercise` | exercise id or null | Must be an exercise the person can see. |
| `what_helped` | string up to 200 characters | Optional. Encrypted at rest. |

### GET /episodes
Newest first, paginated.

### POST /episodes

```json
{
  "occurred_at": "2026-10-12T09:30:00+05:30",
  "intensity": 4,
  "duration_minutes": 20,
  "trigger": "c1d6f5a2-4a0b-4a3e-9e0a-9a1a4b9d2e77",
  "helped_exercise": "7d0f7d5e-1c1c-4f5e-8c11-2c0c2a8f3b10",
  "what_helped": "Calling my sister"
}
```

Only `occurred_at` and `intensity` are required. `201` returns the episode with its `id` and `created_at`.

Errors (`400`):
- `{"occurred_at": ["This time is in the future. Choose now or earlier."]}`
- `{"intensity": ["Ensure this value is less than or equal to 5."]}`
- `{"trigger": ["Invalid pk \"...\" - object does not exist."]}` for an unknown trigger **and** for a trigger that belongs to someone else. The two cases are indistinguishable on purpose.

### GET, PUT, PATCH, DELETE /episodes/{id}
Read, change or remove one episode.

## Exercises

Shared, curated content. Only content approved by a reviewer is served. In development, `SHOW_UNREVIEWED_CONTENT=true` also serves placeholders, with `"reviewed": false`; production ignores that switch.

### GET /exercises
Filters: `?category=` (`grounding`, `breathing`, `journaling`, `planning`, `movement`, `wind_down`), `?lang=` (`en`, `hi`; defaults to the person's language, falling back to English), `?include_hidden=true`.

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "7d0f7d5e-1c1c-4f5e-8c11-2c0c2a8f3b10",
      "slug": "paced-breathing-4-6",
      "category": "breathing",
      "duration_minutes": 3,
      "pattern": {"inhale": 4, "exhale": 6},
      "title": "Slow breathing",
      "summary": "Breathe in for four, out for six. Stop whenever you like.",
      "steps": ["Sit or stand in a way that feels steady.", "..."],
      "language": "en",
      "hidden": false,
      "reviewed": true
    }
  ]
}
```

Exercises the person has hidden are left out unless `include_hidden=true`.

### GET /exercises/{id}
One exercise. `404` if it does not exist or is not approved.

## Exercise events

A person's own optional feedback on an exercise.

| `kind` | Meaning |
|---|---|
| `completed` | Finished the exercise. |
| `helpful` / `not_helpful` | Optional feedback. |
| `hidden` | "Hide this": remove it from my list. |
| `unhidden` | Show it again. The most recent of `hidden` / `unhidden` wins. |

### POST /exercise-events

```json
{"exercise": "7d0f7d5e-1c1c-4f5e-8c11-2c0c2a8f3b10", "kind": "not_helpful"}
```

`201` `{"id": "...", "exercise": "...", "kind": "not_helpful", "created_at": "..."}`.
`400` for an unknown `kind`, or an exercise that does not exist or is not approved.

### GET /exercise-events
The person's own events, newest first, paginated.

### GET, DELETE /exercise-events/{id}
Read or remove one event. Events cannot be edited (`405`).

## Safety plan

One plan per person, in their own words. Everything written is encrypted at rest. There is no id in the URL: the plan always belongs to the signed-in person.

### GET /safety-plan
Before anything is saved, returns an empty plan (and stores nothing):

```json
{"warning_signs": [], "coping_steps": [], "people": [], "resource_ids": [], "updated_at": null}
```

### PUT /safety-plan
Creates or replaces the plan. Each list holds up to 12 lines of up to 200 characters; blank lines are dropped.

```json
{
  "warning_signs": ["Skipping meals", "Not replying to messages"],
  "coping_steps": ["Walk to the end of the road", "Slow breathing for three minutes"],
  "people": ["Meera, my sister"],
  "resource_ids": ["3b1f2c9e-5a44-4c1d-9f0e-8d7c6b5a4e21"]
}
```

`200` returns the saved plan with `updated_at`.
`400`: a list with more than 12 lines, a line over 200 characters, a value that is not a list, or a `resource_ids` entry that is unknown or not verified.

### DELETE /safety-plan
Removes the plan. `204`.

## Resources

### GET /resources (public)
Helplines and services that a named person has verified. Public, so they can be shown before sign-up and cached for offline use. Filters: `?region=IN` (also matches `IN-KA`), `?language=hi`, `?type=` (`helpline`, `emergency`, `text_line`, `campus`, `online`).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3b1f2c9e-5a44-4c1d-9f0e-8d7c6b5a4e21",
      "slug": "in-tele-manas",
      "name": "Tele-MANAS",
      "description": "...",
      "type": "helpline",
      "region": "IN",
      "languages": ["en", "hi"],
      "phone": "14416",
      "url": "",
      "hours": "",
      "source": "...",
      "verified_on": "2026-10-01",
      "stale": false,
      "reviewed": true
    }
  ]
}
```

- Only entries with status `approved` are returned. In development, `SHOW_UNREVIEWED_CONTENT=true` also returns placeholders with `"reviewed": false`.
- `stale` is `true` when the entry was last verified more than `RESOURCE_MAX_AGE_DAYS` (90) ago, or never. Stale entries are still listed so the screen can flag them.
- The seeded entries are unverified placeholders (NEEDS_HUMAN_REVIEW) and are hidden in production until a person verifies them.

### GET /resources/{id} (public)
One entry. `404` if unknown or not verified. The directory is read-only (`405` for writes).

## Trusted contacts

People the student chooses. A contact gets no account and sees no records. Name, email and relationship are encrypted at rest. Up to 3 contacts.

| Status | Meaning |
|---|---|
| `pending` | Invited. Nothing else can be sent to them. |
| `confirmed` | They accepted. They can receive the weekly note (if turned on) and a Support message. |
| `declined` | They said no. Final. |
| `unsubscribed` | They unsubscribed from an email. |
| `bounced` | Their mail server permanently rejected a message. |
| `unavailable` | The address has asked not to receive email from this app. No invitation was sent. |

### GET /trusted-contacts
The student's own contacts.

### POST /trusted-contacts
Limit: 10 a day (shared with re-sending invitations). Sends one invitation email.

```json
{"name": "Meera", "email": "meera@example.com", "relationship": "sister"}
```

`201`:

```json
{"id": "467425ab-775c-4869-b3d7-48995991a617", "name": "Meera", "email": "meera@example.com", "relationship": "sister", "status": "pending", "invited_at": "2026-10-12T04:40:00Z", "responded_at": null, "created_at": "2026-10-12T04:40:00Z"}
```

Errors (`400`, `{"detail", "code"}`):

| `code` | Meaning |
|---|---|
| `display_name_required` | Add a display name first, so the contact knows who is asking. |
| `own_email` | The student's own address. |
| `duplicate_contact` | Already added. |
| `too_many_contacts` | 3 already exist. |

### GET, PATCH, DELETE /trusted-contacts/{id}
`PATCH` changes `name` or `relationship` only; the address cannot be edited. `DELETE` removes the contact and withdraws every consent involving them (`204`).

### POST /trusted-contacts/{id}/resend-invitation
At most 3 invitations in total, at least 24 hours apart. `400` codes: `not_pending`, `invitation_too_soon`, `invitation_limit`, `unavailable`.

## Links opened by a contact (public)

The contact has no account. A signed token from their email is the only credential, sent in the request body. All of these need the CSRF header, and are limited to 30 an hour per address. An invalid or expired token answers `400` `{"detail": "This link is not valid or has expired.", "code": "invalid_link"}`.

| Route | Body | Result |
|---|---|---|
| `POST /contact-invitations/view` | `{"token"}` | `{"from_name", "status", "what_you_may_receive", "limits"}`. The only student data shown is their display name. |
| `POST /contact-invitations/accept` | `{"token"}` | Contact becomes `confirmed`. Repeating it is harmless. |
| `POST /contact-invitations/decline` | `{"token"}` | Contact becomes `declined`. A later accept answers `400` `invitation_closed`. |
| `POST /unsubscribe` | `{"token", "block_all": false}` | Contact becomes `unsubscribed` and every consent involving them is withdrawn. `block_all: true` also stops every message from this app to that address, for any student. |
| `POST /unsubscribe/one-click?token=...` | none | Same as unsubscribe. This is the target of the `List-Unsubscribe` email header, called by mail providers, so it takes no cookie and no CSRF token. |

Invitation links last 14 days. Unsubscribe links do not expire.

## Sharing and consent

Sharing is off until the student turns it on. The list of consents is also the consent history: withdrawing keeps the row.

### GET /sharing/notices (public)
The notice versions a consent request must quote, and the weekly notice text.

### GET /sharing/preview?contact={id}
The exact weekly note, before anything is turned on. Turns nothing on and sends nothing.

```json
{
  "recipient": {"id": "467425ab-...", "name": "Meera", "email": "meera@example.com"},
  "recipient_can_receive": true,
  "subject": "Weekly note from Asha Rao",
  "body": "Asha Rao uses Mirrorspace and chose to send you this short note each week.\n\nWeek of 5 October 2026 to 11 October 2026: checked in 3 of 7 days.\n\nThis is a routine weekly note. Silence does not mean anything either way.\n\nMirrorspace is a self-help tool. It is not monitored by anyone and it is not an emergency service.\n\nTo stop receiving these messages: [a personal unsubscribe link]",
  "fields_shared": ["display_name", "week_start", "week_end", "check_in_days"],
  "values": {"display_name": "Asha Rao", "week_start": "2026-10-05", "week_end": "2026-10-11", "check_in_days": 3},
  "notice": {"purpose": "...", "shared": ["..."], "never_shared": ["..."], "limits": ["..."], "control": "..."},
  "notice_version": "2026-10-placeholder-1",
  "preview_hash": "9f2c...64-hex-characters",
  "default_schedule": {"send_weekday": 0, "send_hour": 9},
  "reconfirm_every_days": 90
}
```

`400` `invalid_contact` for a missing, malformed, unknown or someone else's contact id (all identical).

### GET /sharing/consent
Every consent the student has given, newest first.

```json
{
  "id": "0c7d...", "purpose": "weekly_summary", "contact": "467425ab-...",
  "scope": ["display_name", "week_start", "week_end", "check_in_days"],
  "notice_version": "2026-10-placeholder-1",
  "status": "active", "status_reason": "",
  "granted_at": "2026-10-12T04:45:00Z", "last_confirmed_at": "2026-10-12T04:45:00Z",
  "paused_at": null, "revoked_at": null,
  "send_weekday": 0, "send_hour": 9, "next_send_at": "2026-10-19T03:30:00Z"
}
```

`send_weekday` is 0 (Monday) to 6; `send_hour` is 0 to 23, in the student's own time zone. `next_send_at` is UTC and is `null` whenever the consent is not active.

### POST /sharing/consent
Turns the weekly note on for one contact.

```json
{
  "purpose": "weekly_summary",
  "contact": "467425ab-775c-4869-b3d7-48995991a617",
  "notice_version": "2026-10-placeholder-1",
  "preview_hash": "9f2c...from-the-preview",
  "confirmed": true,
  "send_weekday": 0,
  "send_hour": 9
}
```

`201` returns the consent. Nothing is emailed at this point. Every condition is required; `400` otherwise:

| `code` or field | Meaning |
|---|---|
| `confirmed` | Missing or not `true`. |
| `preview_required` | No contact or no preview hash. |
| `invalid_contact` | Not one of the student's contacts. |
| `contact_not_confirmed` | The contact has not accepted the invitation. |
| `notice_outdated` | The notice changed since it was shown. |
| `preview_outdated` | The message wording changed since the preview. |
| `already_enabled` | A live consent already exists for this contact. |

Recording that the privacy notice was read uses the same route: `{"purpose": "privacy_notice", "notice_version": "...", "confirmed": true}`.

### DELETE /sharing/consent/{id}
Withdraws consent. `200` with the consent, now `status: "revoked"`, `revoked_at` set and `next_send_at: null`. The row is kept. Repeating the call is harmless.

### POST /sharing/consent/{id}/pause, /resume, /confirm
- `pause`: stops the schedule. `400` `not_active` unless active.
- `resume`: restarts it and counts as a fresh confirmation. `400` `not_paused`, `contact_not_confirmed` or `notice_outdated`.
- `confirm`: refreshes `last_confirmed_at`. A weekly note that is not confirmed for 90 days pauses itself with `status_reason: "reconfirmation_needed"`.

Consents cannot be edited (`405` for `PUT` and `PATCH`).

## Support (SOS)

A message the student chooses to send to a confirmed contact. Nothing else in the system can send it. The text is fixed and cannot be edited.

### POST /sos/preview
Body `{"contact": "<id>"}`. Shows the exact recipient and exact text. Sends nothing and records nothing.

```json
{
  "recipient": {"id": "467425ab-...", "name": "Meera", "email": "meera@example.com"},
  "recipient_can_receive": true,
  "subject": "Asha Rao would like to hear from you",
  "body": "Asha Rao asked Mirrorspace to send you this message.\n\nThey are having a difficult moment and would like to hear from you. ...\n\nTo stop receiving these messages: [a personal unsubscribe link]",
  "message_hash": "5d1a...64-hex-characters",
  "limits": "This app is not monitored. It cannot tell you whether the message was read, and it cannot guarantee a reply."
}
```

### POST /sos/notify-contact
Limits: 3 an hour and 6 in 24 hours.

```json
{
  "contact": "467425ab-775c-4869-b3d7-48995991a617",
  "message_hash": "5d1a...from-the-preview",
  "idempotency_key": "a3c1e2f4-6b7d-4e8f-9a0b-1c2d3e4f5a6b",
  "confirmed": true
}
```

`idempotency_key` is a UUID the client generates once per send attempt. Repeating the request with the same key (a double tap, a retry on a bad connection) sends one message.

`202`:

```json
{
  "notification_id": "465acb65-d327-47b5-9d7f-6a3e169b38ba",
  "status": "pending",
  "detail": "Your message is queued to send. This app cannot tell you whether it has been read. If you need support now, you can call a helpline."
}
```

The reply never says "sent" or "delivered". Follow the status at `GET /notifications/{id}`.

`400` (nothing is sent in any of these cases):

| `code` or field | Meaning |
|---|---|
| `confirmed` | Missing or not `true`. |
| `invalid_contact` | Not one of the student's contacts. |
| `contact_not_confirmed` | The contact has not agreed to receive messages. |
| `preview_outdated` | The hash does not match what would be sent now (different contact, changed display name, changed wording). |
| `sos_daily_limit` | 6 already sent in 24 hours. |

`429` when the hourly limit is reached.

## Notifications

### GET /notifications and GET /notifications/{id}
What was sent on the student's behalf and what happened to it. Read-only. There is no message text.

```json
{"id": "465acb65-...", "purpose": "sos", "contact": "467425ab-...", "status": "sent", "status_code": "", "scheduled_at": "2026-10-12T04:50:00Z", "sent_at": "2026-10-12T04:50:02Z"}
```

| `status` | Meaning |
|---|---|
| `pending` / `sending` | Waiting or in progress. |
| `sent` | The email provider accepted it. This does **not** mean it reached an inbox or was read. |
| `cancelled` | Not sent. `status_code` says why: `consent_inactive`, `contact_not_confirmed`, `contact_removed`, `address_suppressed`, `account_closed`, `invitation_closed`. |
| `failed` | Could not be sent: `provider_unavailable` (gave up after 5 attempts), `outcome_unknown`, `unexpected_error`. |
| `bounced` | The recipient's mail server permanently rejected it. The contact becomes `bounced` and consent is withdrawn. |

### POST /webhooks/email-events
For the email provider, not for the frontend. Requires the header `X-Webhook-Secret`; answers `404` when `EMAIL_WEBHOOK_SECRET` is not configured and `403` for a wrong secret.

```json
{"provider_reference": "<message-id-returned-when-sending>", "event": "bounced"}
```

`event` is `bounced` or `complained`. `200` `{"handled": true}`, or `false` when the reference is unknown.

## Chat

An AI companion for reflection and reviewed self-help material. It is not a therapist, and nobody monitors it. Every message passes a safety check in code before it can reach an AI provider.

### GET /chat/info (public)
What the chat is and is not, shown before the first message.

```json
{
  "disclosure": {
    "identity": "I am an AI, not a therapist, a counsellor or a doctor.",
    "can": "I can reflect back what you say, share short pieces of reviewed material, and help you find one small next step.",
    "cannot": "I cannot diagnose, advise on medication or treatment, or help in an emergency. Nobody monitors this chat, and I cannot contact anyone for you.",
    "retention": "Nothing you write here is saved unless you turn on saving. Your message is sent to an AI provider to produce a reply, without your name or any of your records."
  },
  "max_message_length": 1000,
  "max_retention_days": 30,
  "transcripts_saved_by_default": false,
  "signed_in": true
}
```

### POST /chat/sessions
Starts a conversation. Body is optional: `{"save_transcript": false, "retention_days": 30}`. Saving is off unless asked for; `retention_days` is 1 to 30.

`201` `{"id": "...", "save_transcript": false, "retention_days": 30, "expires_at": null, "created_at": "...", "messages": []}`

### GET /chat/sessions, GET /chat/sessions/{id}
The person's own conversations. `messages` is empty unless saving is on.

### PATCH /chat/sessions/{id}
`{"save_transcript": true}` turns saving on (and sets `expires_at`). `{"save_transcript": false}` turns it off **and deletes what was saved**.

### DELETE /chat/sessions/{id}
Deletes the conversation and any saved messages. `204`.

### POST /chat/sessions/{id}/messages
Limit: 10 a minute, plus a daily number of AI replies per person.

```json
{
  "text": "How many hours of sleep do students usually need?",
  "history": [
    {"role": "user", "content": "an earlier message"},
    {"role": "assistant", "content": "an earlier AI reply"}
  ]
}
```

`text` is required, up to 1000 characters. `history` is optional: with saving off, the browser holds the conversation and sends the last few turns back (at most 6 are used). With saving on, the server uses its own saved turns and ignores `history`.

`200`:

```json
{
  "kind": "answer",
  "text": "From the reviewed material: ...",
  "sources": [{"title": "Sleep basics for students", "source": "..."}],
  "actions": [],
  "level": null
}
```

| `kind` | Meaning | Written by |
|---|---|---|
| `answer` | A reply grounded in reviewed passages. `sources` lists them. | The AI |
| `safety` | The message suggested a crisis (`level: "crisis"`) or acute distress (`level: "distress"`). `actions` lists routes the person can choose: Support, their safety plan, helplines, a trusted contact. | People (fixed text) |
| `unsupported` | No reviewed material covers the question. No model was asked. | People (fixed text) |
| `unavailable` | The AI provider did not respond. | People (fixed text) |
| `limit` | Today's AI replies are used up. | People (fixed text) |
| `off_policy` | The provider declined, or the model's reply broke the rules (a diagnosis, medication advice, a claim of monitoring) and was discarded. | People (fixed text) |

A `safety` reply is produced before any budget or provider check, so it is returned even when the limit is reached or the provider is down. Nothing is sent to anyone because of it.

`400` for an empty or over-long `text`. `404` for a conversation that does not exist or belongs to someone else. `429` over the per-minute limit.

### POST /chat/feedback
`{"session": "<id or null>", "kind": "answer", "helpful": false}`. A rating only; there is no text field. `201`.

### GET /chat/feedback, GET and DELETE /chat/feedback/{id}
The person's own ratings.

## Vent

Free writing. Nothing is stored unless the student keeps an entry.

### POST /vent/reflect
Limit: 30 a minute. Body `{"text": "..."}`, 1 to 5000 characters. Stores nothing and logs nothing.

```json
{"reaction": "heavy", "level": null}
```

`reaction` is one of `listening`, `heavy`, `racing`, `storm`, `alone`, `lighter`, `steady`. `level` is `"crisis"` (reaction `steady`), `"distress"` or `null`. Crisis and distress come from the same check as the chat. Nothing is sent to anyone because of either.

### GET, POST /vent-entries; GET, DELETE /vent-entries/{id}
Entries the student chose to keep: `{"id", "body", "created_at"}`, newest first. `body` is 1 to 5000 characters and encrypted at rest. Entries cannot be edited (`405`). They are included in `GET /export` as `vent_entries`.

### GET, PUT /chat/context (decision B83)
`{"enabled": false, "preview": "..."}`. `PUT {"enabled": true}` lets the AI see the summary shown in `preview`, which is exactly what it receives. Off by default. Replies to messages may now include `plan: {"matched": [...], "coping_steps": [...], "href": "/plan"}` when sharing is on and the message mentions one of the student's own triggers; otherwise `plan` is `null`.

### Changes on 2026-10-17 (decision B74)

`POST /chat/sessions/{id}/messages` no longer returns `kind: "unsupported"`. A message with no matching reviewed material is answered by the AI as conversation, with `sources: []`. The `history` the client sends may now include up to 20 earlier turns.
