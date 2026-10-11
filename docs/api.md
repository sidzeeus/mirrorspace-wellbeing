# API reference

Base path: `/api/v1`. The machine-readable description is at `GET /api/v1/schema` (OpenAPI 3; staff only in production).

This file documents the routes that exist today (Phases 1 and 2). It is updated with each phase.

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
  "exercise_events": [{"id": "...", "exercise": "five-senses", "kind": "not_helpful", "created_at": "..."}]
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
