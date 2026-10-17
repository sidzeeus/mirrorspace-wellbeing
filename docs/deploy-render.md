# Deploying the public demo on Render

The whole app runs on Render's free plan from `render.yaml`:

| Render resource | What it runs |
|---|---|
| `mirrorspace-web` (web service) | The Next.js frontend. It also forwards `/api/v1/*` to the API, so the browser talks to one site and the session cookies are first-party. |
| `mirrorspace-api` (web service) | Django, the Celery worker and the Celery scheduler in one container (`backend/start-all.sh`). Free plans have no background-worker service. |
| `mirrorspace-db` | PostgreSQL with pgvector. |
| `mirrorspace-redis` | Key Value (Redis): cache, rate limits and the job queue. |

Chat uses a hosted model (Groq, free tier) instead of Ollama, and email goes out through Brevo's HTTPS API, because free Render services cannot open SMTP connections.

## Before you start: three free accounts

1. **Groq**: create a key at https://console.groq.com/keys. It is `LLM_API_KEY`.
2. **Brevo**:
   - At https://app.brevo.com, add and verify a sender under *Senders, domains & dedicated IPs* > *Senders*. Your Gmail address works. This address becomes `DEFAULT_FROM_EMAIL`.
   - Create an API key under *SMTP & API* > *API keys*. It is `BREVO_API_KEY`.
3. **Render**: sign in with GitHub at https://render.com.

Also make one encryption key on your computer:

```bash
docker compose exec web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

It becomes `FIELD_ENCRYPTION_KEYS`. Keep a copy somewhere safe: losing it makes saved Vent entries, safety plans and contacts unreadable.

## Deploy

1. Push the repository to GitHub.
2. In Render, choose **New** > **Blueprint**, pick the repository, and confirm.
3. Render asks for every value it cannot generate. The URLs depend on the service names. If Render had to add a suffix to a name, use the URLs shown on each service's page.

   | Service | Variable | Value |
   |---|---|---|
   | api | `FIELD_ENCRYPTION_KEYS` | the key you made above |
   | api | `FRONTEND_URL` | `https://mirrorspace-web.onrender.com` |
   | api | `API_BASE_URL` | same as `FRONTEND_URL` |
   | api | `CSRF_TRUSTED_ORIGINS` | same as `FRONTEND_URL` |
   | api | `CORS_ALLOWED_ORIGINS` | same as `FRONTEND_URL` |
   | api | `BREVO_API_KEY` | from Brevo |
   | api | `DEFAULT_FROM_EMAIL` | `Mirrorspace <your-verified-sender@gmail.com>` |
   | api | `LLM_API_KEY` | from Groq |
   | api | `DJANGO_SUPERUSER_EMAIL` | your email, for the admin account |
   | api | `DJANGO_SUPERUSER_PASSWORD` | a long, unique password |
   | web | `API_INTERNAL_URL` | `https://mirrorspace-api.onrender.com` |

4. Wait for both services to show **Live**. The first build takes about ten minutes.
5. Once you can sign in to the admin, delete `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` from the api service. The admin is at `https://mirrorspace-api.onrender.com/admin/`.

Values Render fills in itself:
- `DJANGO_SECRET_KEY` and `PSEUDONYM_KEY` (generated once);
- `DATABASE_URL` and `REDIS_URL` (from the database and Key Value);
- `RENDER_EXTERNAL_HOSTNAME`, which the API adds to its allowed hosts.

## Content that needs a reviewer

Production never shows unreviewed content (non-negotiable 8). The start script loads the sample exercises, helplines and reading material, but they stay hidden until someone approves them in the admin. Until then:

- **Helplines** shows only entries a named person has verified. In the admin, open *Resources*, check each number yourself, then set *status* to approved and fill in *verified on*.
- **Exercises** and Sushi's reading passages appear once a qualified reviewer marks them approved (`docs/review-needed.md`, items R1 and R12).

Everything else works from the first deploy: check-ins, Vent, patterns, episodes, the safety plan, sharing and weekly emails, SOS emails, Sounds, Sushi's conversation and voice, offline mode.

## Public demo vs local

| | Local (`docker compose up`) | Public demo (Render) |
|---|---|---|
| AI | Ollama on your computer, `llama3.1:8b`, nothing leaves the machine | Groq, `llama-3.1-8b-instant`; chat text is sent to Groq |
| Email | Mailpit catches everything (or your Gmail over SMTP) | Brevo over HTTPS, at most 100 emails a day |
| Background jobs | separate worker and beat containers | inside the API container; paused while it sleeps |
| Unreviewed content | shown, so you can try it | hidden until approved |
| Speed | instant | first visit after 15 idle minutes takes about a minute (cold start) |
| Data | your machine | free database, deleted by Render after 30 days unless upgraded |

Before sharing the demo widely, the privacy notice must name Groq and Brevo as processors (`docs/review-needed.md` R32).

## After each deploy: check by hand

1. Open the frontend URL. The landing page loads and the theme toggle works.
2. Register. The verification email arrives (check spam), and the link signs you in.
3. Do a check-in and a Vent entry, then open Patterns.
4. Chat with Sushi. A reply arrives within a few seconds. If the chat says the AI is unavailable, check `LLM_API_KEY` and the API logs for `chat_provider_error`.
5. Add a trusted contact. The invitation email arrives at that address.
6. Press SOS. The Support page loads, and it also loads with the network off once visited.
7. Narrow the browser to phone width: navigation, the SOS button and forms all fit.
8. Sign out, and sign in with a wrong password: you get a clear error message, not a crash.

## When something is wrong

- **The site loads but every action fails:** `API_INTERNAL_URL` on the web service is wrong, or the API is still starting. Open `https://<api>/api/v1/ready`; it should return `"status":"ok"`.
- **"CSRF verification failed" or you are signed out at once:** `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` must exactly match the frontend URL, with `https://` and no trailing slash.
- **No emails:** check the sender is verified in Brevo and `DEFAULT_FROM_EMAIL` uses it. The API logs show `notification_failed` or retries, never addresses.
- **Weekly emails late:** the free API sleeps when idle and the scheduler sleeps with it. A paid instance, or a separate worker service, removes this.
