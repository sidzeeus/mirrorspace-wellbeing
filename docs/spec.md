# Student Mental Wellbeing App: Build specification

> Moved from the repository's README.md on 2026-10-17; the README is now a project overview. Later changes are recorded in `docs/decisions.md`.

This specification is the single source of truth for building the app with Claude Code. It has five parts:

| Part | What it is |
|---|---|
| [A. Locked decisions](#a-locked-decisions) | Judgment calls resolved up front so nothing is guessed. Edit anything you disagree with before starting. |
| [B. Working method](#b-working-method) | How to run the build: phase by phase, tests first, human review where needed. |
| [C. Frontend UI/UX direction](#c-frontend-uiux-direction) | The visual and interaction identity: dark, luminous, cinematic, and calm. |
| [D. Claude Code prompts](#d-claude-code-prompts) | Copy-paste prompts, in build order, with acceptance criteria. |
| [E. Original technical blueprint](#e-original-technical-blueprint) | The full blueprint, included unchanged. |

> **Precedence rule:** if Part A, C or D conflicts with Part E, Part A wins for decisions, Part C wins for design, and Part E wins for everything else. Safety and privacy rules in Part E are never relaxed by any prompt.

---

## A. Locked decisions

These fill the gaps the blueprint leaves open. They are proposed defaults. Change them here (not mid-build) and they flow into `CLAUDE.md` and `docs/decisions.md`.

| Topic | Decision |
|---|---|
| Age policy | **18+ only** for the prototype. Age confirmation at registration. No minors' data collected. Revisit only after India-qualified legal review. |
| Authentication | **Django session cookies + CSRF.** Frontend and API on the same site or sibling subdomains (e.g. `app.example.com` and `api.example.com`) with `SameSite=Lax`, `Secure`, `HttpOnly`. No JWT in `localStorage`. Strict CORS allowlist. |
| Weekly contact email content | Only: the student's display name, the week covered, **"checked in X of 7 days"**, and a fixed neutral line (e.g. "This is a routine weekly note. Silence does not mean anything either way."). No scores, notes, triggers, chats, or risk labels. The student previews and confirms before the first send and can pause or revoke at any time. |
| Check-in free-text notes | **Omitted in the MVP.** Structured fields only (mood, sleep, energy, stress). If added later: field-encrypted, excluded from logs, exports to email, and chat context. |
| Deletion vs audit retention | On account deletion, all user content is deleted or queued for deletion. Audit and consent events are **pseudonymized** (user ID replaced by a one-way hash, no message bodies) and kept **12 months**, then purged. Document in `docs/privacy.md`. |
| Trusted-contact flow | **Double opt-in:** the contact receives a confirmation email and must accept before any message is sent. Every email has an unsubscribe link. Rate limits on adding contacts and on SOS sends. |
| Offline safety | Safety plan and verified helpline numbers are available offline via a **PWA service worker** (required, not optional). |
| Automated risk detection | **Out of scope.** No automatic alerts to anyone. Crisis-like chat content triggers a fixed, non-AI safety response showing the user's own safety plan and verified resources. |
| MVP cut line | Build **Phases 1 to 3** first (foundation, core wellbeing, safety and sharing) plus the frontend for them. Chatbot (Phase 4) and Indian-language content come after, but the i18n foundation is built in from the start. |
| Free-text from students to providers | Never sent to analytics or error tracking. Chat content only goes to the AI provider with minimal context, and transcripts are off by default. |
| Languages | English first. Interface built with `next-intl` so Hindi and other Indian languages can be added by translation files only. Reviewed by fluent speakers before release. |

### Non-negotiables (copied into `CLAUDE.md`)

1. No diagnosis, treatment claims, or promises of suicide prevention anywhere in copy or code.
2. All sharing is **off by default**, explicit, specific, previewable, and revocable.
3. No automatic risk alerts or trusted-contact notifications from a classifier.
4. SOS messages require an explicit user action and show the exact recipient and message first.
5. Never claim the app is monitored, or that an alert was sent, unless that is true and confirmed.
6. No sensitive text (notes, chats, messages) in logs, task names, queue metadata, Sentry, or analytics.
7. Every user-owned query is filtered by the authenticated user. Every such endpoint has a cross-user access test.
8. Clinical content, helpline numbers, the crisis workflow, and legal/privacy copy are placeholders until a qualified human signs them off.

---

## B. Working method

1. **Build one phase at a time, not everything in one request.** Each phase ends with passing tests, especially the cross-user access and consent tests, before the next phase starts. Never start Phase N+1 with failing tests from Phase N.
2. **Use a coding environment (Claude Code) for the repo.** A multi-service project (Django, Next.js, Celery, Docker, CI) belongs in Claude Code with the repository open. Use chat for specs, design review and decisions.
3. **Keep a `CLAUDE.md` and `docs/decisions.md` in the repo.** They hold the locked decisions and non-negotiables above, so every session starts from the same rules. The first prompt below creates them.
4. **Give acceptance criteria per feature and per API route.** Each prompt below states what "done" means, including request/response shapes and error cases where relevant. Extend them as you refine.
5. **Human review stays with you.** Claude builds the machinery. These need qualified people: clinical exercise content, helpline numbers and verification, the crisis workflow wording, DPDP/legal and privacy notices, and safeguarding review. Anything touching these is marked `NEEDS_HUMAN_REVIEW` in code and docs.

### Session routine

Start every Claude Code session with:

```text
Read CLAUDE.md and docs/decisions.md first. Then run the test suite and tell me the current state: what passes, what fails, what phase we are in. Do not start new work until you have done this.
```

End every session with:

```text
Run the full test suite, lint, and type-check. Update docs/decisions.md and docs/progress.md with what changed, what is unfinished, and any assumptions you made. List anything that needs human review.
```

---

## C. Frontend UI/UX direction

### C.1 The idea

The reference images share one feeling: **a quiet, luminous presence emerging from darkness.** A glowing figure, a hand cradling a point of light, two people reaching toward each other made of drifting particles. These are *references for mood only*. The app must not copy them. It should have its own identity built from the same emotional ingredients.

**Concept: "Night Light."** The interface is a calm dark room, and the one thing that glows is the thing that matters: you, your breath, the next small step. Light is the design language. It brightens when you check in, pulses slowly when you breathe, and dims gently when you rest.

**Design personality:** calm, cinematic, trustworthy, a little mysterious, never clinical, never cutesy, never alarmist.

### C.2 Signature elements (the memorable part)

Spend boldness here and keep everything else quiet and disciplined.

1. **The Lumen:** a living particle orb rendered with dithered/halftone dots (inspired by the dot-matrix hand-and-light reference). It is the app's signature object. It appears in the landing hero, the check-in screen, and the breathing exercise. It is **never decoration**; it always reflects something:
   - On check-in, its brightness, density and hue respond to the mood slider, so the student *sees* their answer.
   - In breathing exercises, it expands and contracts on the breathing rhythm.
   - On the dashboard, it shows a soft, non-judgmental summary of the week (more dots lit means more check-ins, not "better mood").
2. **Dot-matrix imagery:** hero art and empty states use dithered particle illustrations (a figure, two hands meeting, a lit window) generated from code or from stylized assets. They suggest connection and support without showing faces or clinical imagery.
3. **Hairline structure:** thin 1px grid lines, small corner crop marks around key panels, and subtle registration marks, used only where they frame content (hero, SOS panel, Lumen stage), not sprinkled everywhere.
4. **Typography contrast:** large, light-weight, tightly-set headlines paired with a quiet monospace for data (dates, counts, timers). Headlines in two tones (bright and dimmed) to create rhythm in long statements, as in the reference footer.

### C.3 Visual system

Claude Code may refine values within reason, but must keep the roles. All colors must pass **WCAG AA contrast** (AAA for body text where feasible).

**Dark theme ("Night", default)**

| Token | Role | Value |
|---|---|---|
| `--ink` | Page background | `#06070C` |
| `--surface` | Panels, cards | `#0E1018` |
| `--surface-raised` | Modals, popovers | `#161926` |
| `--line` | Hairlines, borders | `rgba(237,235,255,0.12)` |
| `--moon` | Primary text | `#EDEBFF` |
| `--moon-dim` | Secondary text | `#9B9AB8` |
| `--lumen` | Primary accent (the glow) | `#7C74F2` periwinkle, with a lighter `#B9B4FF` for highlights |
| `--calm` | Positive / completed | `#7FD6C2` soft teal |
| `--warm` | Attention / gentle warning | `#F2C078` soft amber |
| `--care` | SOS and support actions | `#F29BA8` soft rose (warm and reassuring, not alarm red) |

**Light theme ("Daybreak", user-selectable)**

A pale, cool-white version: background `#F5F6FB`, text `#14152A`, same accent hues darkened to pass contrast. Respect `prefers-color-scheme` on first visit, then remember the user's choice. Both themes are first-class; do not ship Daybreak as an afterthought.

**Typography**

| Role | Suggested face | Notes |
|---|---|---|
| Display and body | A refined, light-weight grotesk (e.g. *Hanken Grotesk* or *Instrument Sans*) | Display at weight 300 to 400, tight tracking, large sizes. Body at 400 for readability. |
| Data and small labels | A quiet monospace (e.g. *Geist Mono* or *IBM Plex Mono*) | Dates, counts, timers, consent versions. |
| Indian scripts | *Noto Sans* family (Devanagari, Tamil, Telugu, Bengali, etc.) | Larger line-height for these scripts; test with fluent speakers. |

Rules: body line length under 75 characters, sentence case everywhere, no all-caps labels, no stacked eyebrow labels above every heading, base size 16px minimum with a user "larger text" setting.

**Shape, space and depth**

- Mixed radii by hierarchy: sharp hairline frames for structural panels, softly rounded (12 to 20px) for interactive controls, fully round for the Lumen and primary buttons. Do not apply one radius to everything.
- Depth comes from glow and layered translucency (`backdrop-filter` glass panels, with a solid fallback), not from grey drop shadows.
- Generous spacing; one idea per screen on mobile.

### C.4 Motion and interaction

Motion is the "dynamic" part, but it must be **purposeful and calm**.

- **One orchestrated moment per page**, not scattered effects: the hero Lumen assembling from particles on first load, the check-in orb responding to input, the dashboard week-summary settling in. Everything else is quiet.
- **Responsive motion:** hover/press states, expanding panels, confirmation transitions that show what changed.
- **Scroll storytelling on the landing page only:** scroll-driven sections where the Lumen transforms (single point of light, then a figure, then two figures reaching), tied to the three-part product promise.
- **Page transitions:** soft cross-fades of 200 to 300 ms. No sliding, bouncing or spinning.
- **Breathing exercise:** the Lumen expands and contracts with a visible, adjustable pace (e.g. 4-in, 6-out), with optional haptic and audio cues.
- **Reduced motion:** with `prefers-reduced-motion` (and an in-app toggle), replace all animation with static states or simple fades. Breathing guidance falls back to text and a simple progress ring.
- **Low-bandwidth mode:** a settings toggle (and automatic on slow connections) replaces canvas/WebGL with static dithered images, skips non-essential fonts and loads no heavy assets.
- **Performance budget:** Lighthouse performance 90+ on mobile for core app screens; the particle canvas must hold 60 fps on mid-range phones or degrade automatically (reduce particle count, then fall back to static). Lazy-load the landing hero scene.
- **No dark patterns:** no streaks, no guilt copy ("you missed a day!"), no confetti, no gamified scores. Skipping is always easy and never penalized.

### C.5 Layout and navigation

- **Mobile-first, desktop-excellent.** Most students will use phones.
- **Mobile:** bottom navigation with Home, Check in, Exercises, Plan, More. A persistent, always-visible **Support** button (SOS) that is high-contrast, one tap away on every screen, and works offline.
- **Desktop:** a slim left rail with the same destinations, a spacious central stage, and an optional right panel for context (today's suggestion, quick resources).
- Wide screens use hairline-framed regions with corner marks around the primary stage; mobile simplifies to full-bleed panels.
- Keyboard navigable everywhere, with visible focus rings in the accent color and logical tab order.

### C.6 Screens and their purpose

| Screen | Purpose and key UX |
|---|---|
| **Landing** (public) | Cinematic hero: dim room, Lumen assembling, headline in two tones (for example "Notice your patterns. Find one small step." then "Reach real help when you need it."). Scroll story, a plain-language safety and privacy section (what the app is and is not), a clear "not therapy or emergency service" statement, and a link to verified helplines before sign-up. |
| **Onboarding** | Age confirmation (18+), plain-language privacy and safety notice, optional preferences. Short, skippable steps, a calm progress indicator, no pressure. |
| **Home / Dashboard** | Greeting without gamification, a gentle "check in if you like" card, the week as a Lumen/constellation summary, one suggested small action, quick access to Plan and Support. |
| **Check-in** | Fast, optional, skippable. Mood slider drives the Lumen; sleep, energy, stress as simple large controls. Finishes in under 20 seconds. Ends with one optional exercise suggestion. |
| **Patterns** | Self-reported trends as a soft line or constellation chart with plain-language observations ("on days you slept less, you rated energy lower"). Never diagnosis, prediction or causal claims. Accessible alternative as a table. |
| **Episodes and Triggers** | Quick log with intensity, trigger and "what helped". Manage triggers with preferred actions. Non-diagnostic language. |
| **Exercises** | Browsable short activities (grounding, paced breathing, journaling, planning, movement, wind-down). "Not helpful" and "Hide this" on every item. Full-screen, distraction-free player. |
| **Safety plan** | User-authored warning signs, steps, people and resources. Fast to open, works offline, printable, easy to edit. |
| **Support (SOS)** | Opens a full-screen calm panel with four options: calming exercise, my safety plan, message a trusted person, call a helpline. Messaging shows the exact recipient and text before sending. States clearly: not monitored, cannot guarantee a response. No motion on this screen except an optional breathing aid. |
| **Resources** | Verified helplines with region, language, type, verification date and a call button. Stale entries flagged. |
| **Sharing and consent** | Weekly email setup as a clear step-by-step flow: choose and verify contact, see exactly what is shared, preview, confirm, schedule visible, pause/revoke with one tap. Consent history is visible. |
| **Chat** (Phase 4) | Clear "I'm an AI, not a therapist" banner, limits, retention controls, source references, and a visible Support button that never goes away. |
| **Settings and privacy** | Theme, text size, language, reduced motion, low-bandwidth mode, data export, delete account, consent history. |

### C.7 Copy and tone

- Warm, plain, specific. Short sentences, active verbs, sentence case.
- Buttons say what happens ("Save check-in", "Send this message", "Pause weekly email"), and the same action keeps the same name through the whole flow.
- Errors explain what happened and how to fix it. They do not apologize and are never vague.
- Empty states are invitations, not blank screens.
- Never use clinical labels about the user. Never say "you are anxious/depressed". Never imply the app is watching over them.

### C.8 Accessibility and inclusion (required, not optional)

- WCAG 2.2 AA minimum; screen reader tested; full keyboard support; 44px minimum touch targets.
- Charts have text and table alternatives; color is never the only signal.
- Captions or transcripts for any audio; no flashing content; all animation optional.
- Indian-language typography: correct font stacks, line-height, no truncation of long words, tested at 200% zoom.
- Works on low-end Android devices and slow networks; PWA installable with offline safety plan and helplines.

### C.9 Recommended frontend stack additions

Next.js (App Router) + TypeScript + Tailwind CSS (as in the blueprint), plus: **Framer Motion** for UI transitions, a lightweight canvas/WebGL layer (**OGL** or **three.js**, or plain Canvas 2D for the dither effect) for the Lumen, **next-intl** for localization, **Serwist** (or equivalent) for the PWA service worker, **Radix UI** primitives for accessible components, **TanStack Query** for API state, **Zod** + **React Hook Form** for validation, **Playwright** and **axe-core** for browser and accessibility tests. Keep the Lumen in a single isolated component with a documented fallback chain (WebGL, then Canvas 2D, then static image).

---

## D. Claude Code prompts

Run these in order. Each begins with the shared context line, so you can paste any prompt on its own.

**Shared context line** (already included at the top of every prompt below):

```text
Context: read CLAUDE.md and docs/decisions.md first. This is a mental-wellbeing support prototype for students (18+). It is not therapy, diagnosis, or emergency monitoring. Follow the non-negotiables exactly.
```

### Prompt 0: Bootstrap the repo, CLAUDE.md and decisions

```text
Create the project skeleton and the files that keep every future session consistent.

1. Create the monorepo layout from the blueprint (frontend/, backend/ with config/ and apps/, infra/, .github/workflows/, docs/, docker-compose.yml, Dockerfile.backend, .env.example, README.md).
2. Create CLAUDE.md at the repo root containing: the project purpose, the 8 non-negotiables, the locked decisions table, the tech stack, coding standards (Ruff, mypy optional, pytest, Playwright, ESLint, TypeScript strict), the rule "never put sensitive text in logs, task names, queue metadata, Sentry or analytics", and the session routine (read this file first, run tests first, update docs/progress.md last).
3. Create docs/decisions.md with the locked decisions, each with a one-line rationale and a date, plus an "open questions" section.
4. Create docs/progress.md with the phase checklist from the blueprint roadmap.
5. Mark anything needing clinical, legal or safeguarding sign-off as NEEDS_HUMAN_REVIEW in docs/review-needed.md.

Do not write feature code yet. Show me the tree and the contents of CLAUDE.md when done.

Acceptance: files exist, CLAUDE.md contains all 8 non-negotiables, nothing else is built.
```

### Prompt 1: Phase 1, foundation (backend, infra, CI)

```text
Context: read CLAUDE.md and docs/decisions.md first. Build Phase 1 (Foundation) only.

Backend: Django + Django REST Framework with a CUSTOM user model (UUID pk, email login, preferred_language, created_at) created before the first migration; split settings (base/local/test/production, environment driven); PostgreSQL; session auth with CSRF; strict CORS allowlist; explicit DRF defaults (authentication required, throttle classes and rates, pagination); OpenAPI schema; health and readiness endpoints; structured logging with a redaction filter; Sentry wiring with PII scrubbing.

accounts app: register (with 18+ confirmation), email verification, login/logout, password reset, session expiry, account deletion request. Use a console email backend in local.

Infra: docker-compose with web, worker, beat, db, redis, frontend; Dockerfile.backend with pinned base image, non-root user, no secrets in layers; .env.example with every variable documented.

CI (GitHub Actions): on pull request run ruff, type-check, backend tests, frontend lint/type-check/build.

Tests (pytest-django, DRF APIClient, factory_boy): registration, verification, login/logout, throttling on login, password reset, deletion, and a first cross-user access test harness that later apps will reuse.

Acceptance: docker compose up works; all tests pass; python manage.py check --deploy has no errors with production settings; no secrets in the repo; docs/progress.md updated.
```

### Prompt 2: Phase 2, core wellbeing backend

```text
Context: read CLAUDE.md and docs/decisions.md first. Build the Phase 2 backend (Core wellbeing).

Apps and models as in the blueprint: checkins, episodes (with Trigger), wellbeing (Exercise, Translation, ExerciseEvent).
- Check-ins: mood, sleep duration/quality, energy, stress; NO free-text note in the MVP; one skippable form; local_date + timezone handling; unique constraint on user+local_date; index on user+date.
- Episodes and triggers: user-authored, archivable triggers with preferred exercise IDs; no diagnostic labels.
- Exercises: reviewed content with language, category, review_status, version, review date; "not helpful" and "hide this" via ExerciseEvent; seed command that loads sample content flagged NEEDS_HUMAN_REVIEW.
- Pattern endpoint: simple aggregates of the user's own data (e.g. average sleep vs energy by week) returned with plain-language observation strings that describe correlation only, never diagnosis, prediction or causation.

Endpoints per the blueprint API list (check-ins, episodes, triggers, exercises, exercise-events) plus GET /api/v1/patterns. Every endpoint: authenticated, object ownership enforced in the queryset, input validated, throttled, minimal response fields.

Tests: model constraints; timezone/date logic; validation errors; pagination; and for EVERY user-owned resource a test that user A cannot list, read, update or delete user B's objects. Include data export and deletion covering these new models.

Acceptance: all tests pass, OpenAPI schema updated, docs/api.md documents each route with request/response examples and error cases.
```

### Prompt 3: Phase 3, safety and sharing backend

```text
Context: read CLAUDE.md and docs/decisions.md first. Build the Phase 3 backend (Safety and sharing).

safety app: SafetyPlan (one per user, restricted), resource directory (region, language, type, source, verified_on, owner, status) with a management command that flags entries older than a configurable age. Seed with clearly marked placeholder entries (for India, include Tele-MANAS 14416 as an example flagged NEEDS_HUMAN_REVIEW with the rule that it must be re-verified before each release).

sharing app: TrustedContact (encrypted contact data where feasible), DOUBLE OPT-IN verification (contact must accept via emailed link), unsubscribe link in every email, ConsentRecord (purpose, scope, notice version, status, granted_at, revoked_at, last_confirmation), consent create/withdraw endpoints, and a weekly-message generator that produces ONLY: display name, week range, "checked in X of 7 days", and the fixed neutral line from docs/decisions.md. A preview endpoint returns the exact message before enabling.

notifications app: Notification model with idempotency key (unique), status, retry count, provider reference; Celery tasks that (1) re-check ACTIVE consent immediately before sending, (2) use idempotency keys so duplicates never send twice, (3) retry transient errors with backoff, (4) stop on permanent bounces and expose delivery status, (5) handle the user's timezone and DST. No sensitive text in task names, queue metadata or logs.

SOS: POST /api/v1/sos/notify-contact requires an explicit confirmed request containing the exact recipient ID and message hash the user was shown; rate limited; never triggered by anything automatic.

audit app: record consent and security events with no message bodies; pseudonymize on account deletion per docs/decisions.md.

Tests: no email without active consent; consent revoked between scheduling and sending; duplicate task delivery; bounce handling; timezone/DST correctness; unsubscribe; double opt-in required; SOS requires explicit confirmation and respects rate limits; cross-user access tests for safety plan, contacts, consents.

Acceptance: all tests pass; weekly message content tested against the allowed-fields list so no other field can leak; docs/privacy.md updated.
```

### Prompt 4: Frontend design system and landing page

```text
Context: read CLAUDE.md, docs/decisions.md and the "Frontend UI/UX direction" section of README.md (Part C) first. Build the frontend foundation and public landing page. Follow Part C exactly; the reference images are mood only, do NOT replicate any of them.

Before writing code, produce a short design plan (tokens, type scale, layout concept with ASCII wireframes for the landing page and the app shell). Review the plan against Part C and against generic "AI-looking" defaults (single bright accent on black, identical rounded cards, all-caps eyebrow labels on every heading, fade-and-slide on every section). Revise anything generic, tell me what you changed, then build.

Build:
1. Design tokens as CSS variables + Tailwind config for Night (default) and Daybreak themes, with the theme switcher, prefers-color-scheme support, and persisted choice.
2. Typography setup (display grotesk, mono, Noto Sans for Indian scripts) with next/font, a documented type scale, and a larger-text setting.
3. Core components with Radix primitives: Button, IconButton, Panel (hairline frame with optional corner marks), GlassPanel (with solid fallback), Input, Slider, Toggle, Dialog, Toast, Tabs, ProgressRing, VisuallyHidden, SkipLink. Visible focus rings; 44px touch targets.
4. The Lumen component: an isolated, documented particle/dither orb with props (intensity, density, hue, breathPhase, mode) and a fallback chain WebGL -> Canvas 2D -> static image; honors prefers-reduced-motion and a low-bandwidth setting; auto-degrades below 50 fps.
5. The landing page: cinematic hero with the Lumen assembling once on load, two-tone headline, scroll-driven story (single light -> figure -> two figures reaching) implemented with IntersectionObserver or scroll-timeline and disabled under reduced motion, a plain-language "what this app is and is not" section, a verified-helplines strip visible before sign-up, and a footer. No stock imagery and no placeholder lorem ipsum; write real, specific copy following Part C.7.
6. Playwright + axe-core tests for landing page accessibility, keyboard navigation, theme switching, reduced-motion behavior.

Acceptance: Lighthouse mobile performance >= 90 and accessibility >= 95 on the landing page; no axe violations; works with JS animations disabled; screenshots of both themes at mobile and desktop widths saved to docs/screenshots/.
```

### Prompt 5a: App shell, onboarding and dashboard

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. Build the authenticated app shell and connect it to the real API.

- Auth screens (register with 18+ confirmation, verify email, login, reset password) using session cookies + CSRF via a typed API client (TanStack Query, Zod types generated or derived from the OpenAPI schema).
- App shell: mobile bottom navigation (Home, Check in, Exercises, Plan, More) and a desktop left rail; a persistent Support (SOS) button on every screen that is high contrast, one tap, and never hidden.
- Onboarding: age confirmation, plain-language privacy and safety notice (versioned, recorded as consent), optional preferences (language, theme, text size, reduced motion, low bandwidth). Every step skippable except the age confirmation and notice.
- Dashboard: gentle greeting (no streaks, no guilt copy), optional check-in card, week summary rendered with the Lumen (more lit dots = more check-ins, never "better mood"), one suggested small action, quick links to Plan and Support. Proper empty, loading and error states with direction, not apology.

Acceptance: full keyboard and screen-reader pass; Playwright flow sign up -> verify -> onboarding -> dashboard; both themes; reduced-motion and low-bandwidth modes verified; no console errors.
```

### Prompt 5b: Check-in, patterns, episodes and triggers

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. Build the check-in, patterns, episodes and triggers screens.

- Check-in: finish in under 20 seconds. Mood slider drives the Lumen (brightness, density, hue) in real time with a text equivalent for screen readers; sleep, energy and stress as large simple controls; skip button always visible; no free-text note (per decisions). After saving, offer ONE optional exercise suggestion, with "Not now" equally prominent.
- Patterns: soft line/constellation chart of the user's own data, a plain-language observations list (correlation only), a table alternative, and a date-range control. No diagnosis, prediction or causal wording; add a unit test that scans observation strings for banned phrases.
- Episodes and triggers: quick-log flow with intensity, trigger, duration and "what helped"; manage/archive triggers with preferred exercises. Non-diagnostic language only.

Acceptance: Playwright E2E (sign in -> check-in -> see trend); axe passes; charts have non-visual alternatives; copy reviewed against Part C.7.
```

### Prompt 5c: Exercises and the breathing player

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. Build the exercise library and player.

- Library: browsable by category with sensible filters; "Not helpful" and "Hide this" on every item; shows only content with an approved review_status (placeholder content is clearly labelled in development builds only).
- Full-screen distraction-free player for grounding, journaling-prompt, planning, movement and wind-down exercises.
- Paced breathing player: the Lumen expands and contracts on an adjustable rhythm (default 4-in, 6-out), optional audio and haptic cues, a text/progress-ring fallback for reduced motion, and a gentle "end anytime" control. Record optional helpfulness feedback via exercise-events.

Acceptance: works offline for already-loaded exercises; reduced-motion fallback verified; Playwright test for completing an exercise and marking it not helpful; axe passes.
```

### Prompt 5d: Support (SOS), safety plan and resources

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. These screens are safety-critical; keep them simple, fast and reliable.

- Support (SOS): full-screen calm panel from the persistent button. Four clear options: calming exercise, my safety plan, message a trusted person, call a helpline. Messaging flow shows the EXACT recipient and EXACT message text before sending and requires an explicit confirm tap (no automatic sends, no hidden steps). State plainly: the app is not monitored and cannot guarantee a response. Minimal motion; high contrast; large targets.
- Safety plan: user-authored warning signs, coping steps, chosen contacts and resources; quick to open from anywhere; editable; printable view.
- Resources: verified helplines with region, language, type, verified_on date and a tap-to-call action; stale entries visibly flagged.
- PWA: service worker that caches the safety plan and verified helplines so Support works OFFLINE; test offline behavior; the cache never includes check-ins, episodes or other private data.

Acceptance: Playwright tests for the full SOS send path and the cancel path; offline test passes; axe passes; manual checklist of every string on these screens saved to docs/review-needed.md as NEEDS_HUMAN_REVIEW.
```

### Prompt 5e: Sharing, consent and privacy settings

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. Build the consent and privacy experience.

- Weekly email setup as a clear step-by-step flow: add a contact, contact confirms (double opt-in) with visible status, review exactly what will be shared (only the allowed fields), preview the real message, confirm, see the visible schedule. Pause and revoke are one tap from the main sharing screen. Show delivery status and make clear that missed emails or silence do not indicate safety.
- Consent history screen listing every grant/revoke with notice version and timestamp.
- Settings: theme, text size, language, reduced motion, low-bandwidth mode, data export (download), delete account (confirmation with plain explanation of what is deleted and what pseudonymized audit data remains).

Acceptance: Playwright test: opt in -> contact confirms -> preview -> confirm -> revoke; sharing is OFF by default for new accounts (tested); axe passes; copy follows Part C.7 with no clinical language.
```

### Prompt 6: Localization, PWA and accessibility hardening

```text
Context: read CLAUDE.md, docs/decisions.md and README.md Part C. Complete the localization and accessibility foundation.

- Move every user-facing string into next-intl message files; add a language selector; add Hindi as a second language using placeholder translations flagged NEEDS_HUMAN_REVIEW (do not ship machine translations as final). Verify layouts with long strings and Indian scripts at 200% zoom.
- Full PWA: installable, offline fallback page, update flow.
- Accessibility audit: run axe on every screen, fix issues, add the checks to CI; verify keyboard-only and screen-reader flows for check-in, SOS and sharing.
- Low-bandwidth mode: verify no canvas, no heavy assets, small bundles; add a bundle-size budget to CI.

Acceptance: CI runs axe and bundle budgets; documented manual test script for fluent-speaker review in docs/localization.md.
```

### Prompt 7: Phase 4, AI support chat (only after Phases 1 to 3 and their frontend pass)

```text
Context: read CLAUDE.md and docs/decisions.md first. Build Phase 4 (AI prototype). Only start if all earlier tests pass.

- Provider adapter isolating the hosted LLM API behind an interface so the provider can change; model keys only from environment; per-user and global usage budgets and rate limits; minimal data sent to the provider.
- Curated knowledge pipeline: ContentDocument/Chunk with source, audience, language, review date and approval status; embeddings in pgvector; retrieve a small number of passages; ONLY approved content is indexed.
- Chat policy: clearly an AI, not a therapist; short answers; uncertainty acknowledged; no diagnosis, medication advice or treatment claims; show source references; transcripts OFF by default with retention controls.
- CRISIS WORKFLOW AS SEPARATE CODE, not only a system prompt: a deterministic safety check runs before and after the model; on concerning content, stop routine coaching and show a fixed, human-reviewed message with the user's own safety plan and verified resources and user-directed contact options. Never claim monitoring or that an alert was sent. NO automatic trusted-contact alert from any classifier. Mark the wording NEEDS_HUMAN_REVIEW.
- Frontend: chat UI with the "I'm an AI" banner, limits notice, retention controls, sources, feedback buttons, and the persistent Support button.
- Evaluation set (JSON) covering: grounded answers, unsupported questions, self-harm-like messages, panic, abuse, code-switched and misspelled text, prompt injection, provider outage, rate limits. Tests use a mocked provider; do not call a paid model in CI.

Acceptance: all tests pass with the mocked provider; crisis fallback test passes for every crisis case in the evaluation set; no raw prompts or responses in logs, Sentry or analytics (tested).
```

### Prompt 8: Phase 5, hardening and security review

```text
Context: read CLAUDE.md and docs/decisions.md first. Run a hardening pass across the whole repo.

1. Security review against the blueprint's baseline: HTTPS settings, cookies, CSRF, CORS, SECRET_KEY and key handling, DEBUG off, ALLOWED_HOSTS, secure proxy headers, HSTS, check --deploy, admin restrictions, rate limits, request-size limits, dependency audit (pip-audit, npm audit).
2. Write a test that enumerates EVERY API route and asserts: authentication required (unless explicitly public), ownership enforced, and a cross-user access test exists.
3. Verify retention and deletion: account deletion removes or queues deletion for all user data, exports are complete, audit records are pseudonymized.
4. Log and error-tracking audit: prove no sensitive text appears in logs, task names, Sentry events or analytics (add tests with canary strings).
5. Load check the key endpoints and the weekly email task; backup and restore rehearsal documented.
6. Produce docs/security-review.md listing findings, fixes, and anything left for human review.

Acceptance: all tests pass; findings documented; no high-severity open issues.
```

### Prompt 9: Phase 6, deployment and automation

```text
Context: read CLAUDE.md and docs/decisions.md first. Build deployment and CI/CD.

- Production Docker images (pinned base images, non-root, no secrets in args or layers), health endpoint, graceful shutdown.
- GitHub Actions: PR (lint, type-check, unit/API/privacy tests, frontend build, axe, bundle budget); main (build images, dependency and image scan, publish to GHCR with immutable Git SHA tag plus release tag, never latest-only); deploy (controlled migrations, deploy API + worker + beat, deploy frontend, smoke tests); scheduled checks (resource and exercise review reminders, dependency update PRs, helpline verification reminder to a human owner).
- Environment config for managed PostgreSQL and Redis; secrets via the host's secret store.
- docs/runbook.md: deploy, rollback, migrations, backup/restore, incident steps, who verifies helplines and when.

Acceptance: a tagged release builds and publishes an image reproducibly; smoke tests pass against a staging environment; runbook reviewed.
```

### Prompt 10: Final review (run before any real student use)

```text
Context: read CLAUDE.md and docs/decisions.md first. Act as an independent reviewer of this repository against the blueprint's Definition of Done (Part E, section 14) and the 8 non-negotiables.

For each Definition of Done item, state PASS / FAIL / NEEDS_HUMAN_REVIEW with evidence (file, test name, or command output). Search the codebase and copy for: diagnosis or treatment claims, monitoring claims, automatic alerts, sharing that defaults to on, sensitive text in logs, missing ownership checks, and any placeholder content that could reach production. Output a prioritized fix list and a separate list of items that require clinical, legal, privacy or safeguarding sign-off before launch.
```

### Optional utility prompts

**Add a new feature safely:**

```text
Context: read CLAUDE.md and docs/decisions.md first. I want to add: <feature>. Before writing code, tell me which non-negotiables and data rules it touches, propose acceptance criteria and API shapes, and list tests you will write first (including cross-user access). Wait for my approval, then implement test-first.
```

**Refine the frontend look without breaking accessibility:**

```text
Context: read README.md Part C. I want to change <thing> about the visual design. Propose 2 options that stay within the Night Light concept, show the token changes, verify contrast ratios for every changed color pair, and confirm reduced-motion and low-bandwidth fallbacks still work before applying.
```

---

## E. Original technical blueprint

*The blueprint below is reproduced unchanged in content, including its original wording and the `[web:…]` source markers. Only layout formatting (tables and lists) was adapted to Markdown.*

---

# Student Mental Wellbeing App

Project structure, features, technology stack, data design, safety, testing, and deployment blueprint

## Project purpose

A privacy-first wellbeing companion for students that helps them notice patterns, try small self-help actions, and connect to trusted or professional support when they choose. It is a support and education prototype—not diagnosis, therapy, or an emergency-monitoring service.

Recommended architecture: React/Next.js frontend + Django REST Framework API + PostgreSQL + Celery/Redis for background jobs + a bounded retrieval-augmented chatbot + Docker and GitHub Actions.

## 1. Project overview

The project combines a student-facing web app, a secure backend, a relational database, an AI support companion, consent-controlled communications, and automated deployment. The strongest project contribution is the complete engineering and safety-aware product loop—not the number of features.

### Product hook

"Notice your patterns. Find one small next step. Reach real help when you need it." The app connects lightweight check-ins to relevant micro-exercises and user-controlled pathways to human support.

### Goals

- Make check-ins short, optional, and nonjudgmental.
- Offer practical, small actions rather than claiming to treat mental illness.
- Keep personal data private by default and put users in control of sharing.
- Make access to trusted people and verified local support clear.
- Demonstrate robust backend, database, API, AI, security, testing, and deployment skills.

### Non-goals

- No diagnosis, treatment claims, automated clinical decisions, or promises of suicide prevention.
- No continuous monitoring or guarantee that a trusted contact or helpline will respond.
- No automatic exposure of private mood logs, journal text, chatbot transcripts, or inferred risk labels.

## 2. User roles and journeys

| Role | Purpose / permissions |
|---|---|
| Student user | Own account, check-ins, episodes, triggers, exercises, safety plan, chatbot, contact consents, and data export/deletion. |
| Trusted contact | Receives only specifically consented messages; does not receive an account or access to student records. |
| Admin / content editor | Manages vetted exercises, resources, language text, and helpline directory; access to user data should be restricted. |
| Counsellor (future, optional) | Only receives material the student explicitly chooses to share; not part of MVP. |

### Core journey

1. Student registers, sees a plain-language privacy and safety notice, and configures optional preferences.
2. Student completes a quick mood/sleep check-in or skips it.
3. The app shows a simple personal trend and offers an optional small exercise.
4. The chatbot supports reflection or planning, with clear AI limits.
5. The student can opt in to weekly email sharing and/or explicitly initiate an SOS contact message.
6. Student can review, revoke, export, or delete data and sharing settings.

## 3. Feature requirements

| Feature | MVP behavior / acceptance criteria |
|---|---|
| Authentication | Register, verify email, sign in/out, password reset, session expiry, and account deletion. Use a custom Django user model from the start. |
| Mood/sleep check-ins | Fast daily form with optional mood, sleep duration/quality, energy, stress, and optional note. Skip allowed. User sees only their records. |
| Episode log | Optional event with time, intensity, user-selected trigger, duration, and what helped. Avoid diagnostic labels. |
| Personal triggers | User can add/edit/archive triggers and associate preferred actions. Suggestions are opt-in. |
| Micro-exercises | Short, reviewed grounding, paced breathing, journaling, planning, movement, or wind-down activities. Include "not helpful" and "hide this." |
| Pattern view | Basic trends based on self-reported information; describe correlation/observations, never diagnosis, prediction, or causal conclusions. |
| Indian language support | Localize interface and reviewed content; language selector, readable typography, low-bandwidth mode, and audio/voice input as later enhancement. Test with fluent speakers. |
| AI support chat | Bounded reflective support and approved content retrieval; disclose AI identity, limits, retention, and crisis fallback. Not an AI therapist. |
| Weekly check-in email | Off by default. Verified trusted contact, explicit purpose-specific consent, minimal neutral wording, visible schedule, preview/confirmation, easy pause/revoke, delivery status. No clinical details. |
| SOS flow | User taps SOS, chooses calming exercise, safety plan, message trusted person, or call helpline. Show exact recipient and message before sending. No silent notification for ordinary panic SOS. |
| Safety plan | User-authored warning signs, actions, selected contacts/resources; available quickly and offline if feasible. |
| Resource directory | Admin-reviewed helplines and emergency resources with region, language, type, verification date, and source. Provide call action and check for stale entries. |
| Privacy controls | Plain-language data notice, consent history, retention/deletion, export, contact management, and private-by-default settings. |

### Suggested MVP priorities

Build auth + check-ins + trigger preferences + exercises + privacy controls + consent-based weekly email + user-initiated SOS first. Add AI only after these core flows and safety boundaries work. Treat automated self-harm detection/alerting as out of MVP pending clinical, legal, and safeguarding review.

## 4. Technology stack

| Layer | Recommended choice | Notes |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS | Student dashboard, forms, chat UI, responsive layout. Can deploy on Vercel. |
| API/backend | Django + Django REST Framework | Python API, serializers, validation, permissions, admin, business logic. |
| Database | PostgreSQL | Relational data and migrations; managed provider for hosted deployment. |
| Authentication | Django auth + secure session or token strategy | Use custom user model; select cookie/session vs JWT based on frontend hosting and CSRF/CORS model. |
| Background jobs | Celery + Redis; Celery Beat or managed scheduler | Weekly mail and retries run outside HTTP request. Ensure idempotency. |
| Email | Transactional provider (e.g., Resend/Postmark) | Verified sender/domain, templates, bounce handling, suppression, secrets in environment. |
| AI model | Hosted LLM API or local/open-weight model for prototype | Provider choice depends on data-processing terms, cost, latency, and deployment constraints. |
| Knowledge retrieval | Curated content + embeddings + pgvector (optional) | RAG grounds answers in reviewed materials; it does not by itself make the bot safe or clinically validated. |
| Object storage | S3-compatible private bucket, only if needed | Do not store uploaded sensitive data by default; signed links and limits if used. |
| Containerization | Docker + Docker Compose | Reproducible development; separate web, worker, scheduler, Redis, database services. |
| CI/CD | GitHub Actions + GHCR | Run tests, build image, publish tags, deploy frontend/backend. |
| Monitoring | Sentry + structured logs | Redact personal text, tokens, and sensitive payloads. |

### Keep the stack manageable

Do not add Kubernetes, microservices, a custom-trained foundation model, or a separate vector database for the first version. Start with a modular Django monolith and one PostgreSQL database. Add services only when a concrete requirement justifies them.

## 5. Application architecture

Browser / Next.js frontend → HTTPS API → Django REST Framework → PostgreSQL. Django calls an external model through a provider adapter for normal chat, and queues weekly email/SOS delivery work to Celery through Redis. Knowledge documents are curated and indexed; retrieved passages are passed to the model under restrictive instructions. Email provider and AI provider are external dependencies and must be isolated behind application services.

### Backend Django apps

- accounts: custom user, profile, email verification, preferences, account deletion.
- checkins: mood, sleep, energy, stress logs and user-only list/detail APIs.
- episodes: user-authored episodes, triggers, coping response.
- wellbeing: exercises, categories, localized content, completion feedback.
- safety: user-authored safety plan, SOS actions, resource directory.
- sharing: trusted-contact verification, consent, revocation, weekly message generation.
- chat: sessions, conversation policy, provider integration, retrieval, feedback and safety escalation events.
- notifications: email templates, delivery attempts, retry state, idempotency.
- audit: security-relevant changes and consent events, avoiding sensitive message bodies.
- content_admin: vetted resources, language versions, review status and expiry/verification dates.

### API examples

| Method / route | Purpose |
|---|---|
| POST /api/v1/auth/register | Create student account. |
| POST /api/v1/auth/login; POST /api/v1/auth/logout | Authenticate and end session. |
| GET/POST /api/v1/check-ins | List/create own check-ins. |
| GET/POST /api/v1/episodes | List/create own episodes. |
| GET/POST /api/v1/triggers | List/create user triggers. |
| GET /api/v1/exercises; POST /api/v1/exercise-events | Browse content / record optional feedback. |
| GET/PUT /api/v1/safety-plan | Read/update own safety plan. |
| GET/POST /api/v1/trusted-contacts | Manage own selected contacts. |
| POST /api/v1/sharing/consent; DELETE /api/v1/sharing/consent/{id} | Enable/withdraw weekly sharing. |
| POST /api/v1/sos/notify-contact | Explicitly request one user-approved message. |
| POST /api/v1/chat/sessions; POST /api/v1/chat/sessions/{id}/messages | Chat session/message API with limits and safety handling. |
| GET /api/v1/resources | List verified local support resources. |
| GET /api/v1/export; DELETE /api/v1/account | User data access and deletion workflow. |

All protected endpoints must authenticate, check object ownership, validate input, apply rate limits where appropriate, and return only necessary fields. DRF has configurable authentication, permissions, and throttling; set safe defaults explicitly instead of assuming endpoints are private. [web:197][web:198][web:199]

## 6. Database design

| Entity | Core fields / relations |
|---|---|
| User | UUID, email, password hash, is_active, created_at, preferred_language; custom user model. |
| Profile | user FK unique, display name (optional), timezone, notification preferences, optional age-band only if needed. |
| CheckIn | user FK, local_date/time, mood scale, sleep values, energy/stress optional, optional note encrypted or omitted, created_at. |
| Episode | user FK, occurred_at, intensity, duration, user-entered description optional, trigger FK optional, helpful_action optional. |
| Trigger | user FK, label, active flag, associated exercise IDs/preferences. |
| Exercise / Translation | curated content, language, category, instructions, review status, version/date. |
| ExerciseEvent | user FK, exercise FK, optional helpfulness, created_at. |
| SafetyPlan | user FK unique, warning signs, coping steps, resources/contact preferences; restrict access. |
| TrustedContact | user FK, encrypted contact data where feasible, verified_at, active, relationship optional. |
| ConsentRecord | user FK, recipient FK, purpose, scope, version of notice, status, granted_at, revoked_at, last confirmation. |
| Notification | user FK, purpose, scheduled_at, status, provider reference, retry count; no private message body in logs. |
| ChatSession / Message | user FK, created_at, retention expiry; keep transcripts off by default or minimize, with explicit controls. |
| ContentDocument / Chunk | curated source, approval/version metadata, text chunk, embedding; no personal user chat in public corpus. |
| AuditEvent | actor, action, object type/id, timestamp, minimal metadata; never raw secrets or unnecessary message text. |

### Data rules

- Every user-owned row must be filtered by the authenticated user in every query; add tests for cross-user access.
- Use UUID identifiers if helpful, but UUIDs are not authorization.
- Use timestamps in UTC and store timezone preference for presentation/scheduling.
- Add database constraints and indexes for user + date queries, contact uniqueness, consent state, and notification idempotency.
- Define retention periods and deletion cascades/queues before collecting real personal data.

## 7. AI chatbot design

### Product role

A student support companion for reflective listening, psychoeducation from approved material, brief exercises, and one small next step. It is not a therapist, clinician, diagnostic tool, or emergency response service.

### RAG implementation

1. Create a curated knowledge set authored or reviewed by qualified mental-health professionals. Include citations/source, intended audience, language, review date, and scope.
2. Chunk and embed only approved educational/exercise text; store in pgvector if PostgreSQL extension support is available.
3. For each query, retrieve a small number of relevant passages and provide them as bounded context to the model.
4. Require short, clear answers, uncertainty acknowledgement, and no diagnosis/medication advice. Provide source references inside the app where possible.
5. Add user feedback and a reviewed evaluation set; test harmful, ambiguous, code-switched, misspelled, and crisis-like messages.

### Important distinction

RAG is retrieval over approved content; it is not model training. Fine-tuning is not recommended for the first project version. Never train on real student chats by default. Protect API credentials, minimize data sent to providers, and review provider retention/training policies.

### Crisis boundaries

- Use a separate crisis/safety workflow, not just a system prompt.
- If concerning content appears, respond calmly, stop routine coaching, show the saved safety plan and verified resources, and offer user-directed contact routes.
- Do not say the app is monitored or that an alert was sent unless that is true and confirmed.
- Do not make an automatic trusted-contact alert based solely on a classifier output in the MVP.
- Evaluate false positives/false negatives with qualified reviewers and define a real human response process before any monitoring claim.

## 8. Consent, safety and privacy

Sensitive wellbeing data deserves a stricter standard than an ordinary student productivity app. Make data collection minimal, sharing off by default, and permissions specific. India's notified DPDP Rules call for clear consent notices describing purposes; children's data may require verifiable parent/guardian consent, subject to the applicable exceptions and legal interpretation. Obtain India-qualified legal review before launch, especially if users under 18 may join. [web:216]

### Weekly contact email

- Off by default; the student explicitly opts in and selects/verifies the recipient.
- State purpose, cadence, fields shared, recipient, and how to pause/revoke.
- Keep wording neutral and minimal; let the student preview or approve the message.
- Do not share notes, individual mood scores, diagnoses, chats, triggers, or hidden risk classifications.
- Make it clear that missed emails or silence do not indicate safety. Record consent version/timestamps and delivery status.

### SOS

- Tap is user initiated; show options for a short grounding flow, personal safety plan, trusted-contact message, or calling a listed resource.
- Present exact recipient and message and ask confirmation before sending.
- Offer an undo/cancel window only if it will not undermine a user-requested urgent message.
- State that the app is not continuously monitored and cannot guarantee response.

### India resource example

Tele-MANAS is listed by Indian government sources at 14416 for mental-health support; validate current availability, supported languages, and local emergency details before each release. [web:46][web:52]

### Security baseline

- HTTPS everywhere; secure cookies, CSRF protection, correct CORS allowlist, secure password reset and email verification.
- Keep SECRET_KEY, database credentials, email/API keys, and model keys in secret storage/environment variables, never Git, frontend bundles, or container layers.
- Set production DEBUG=False, ALLOWED_HOSTS, secure proxy headers, HSTS after verification, and run `python manage.py check --deploy`. Django's deployment checklist stresses secrets and database access restrictions. [web:190][web:191]
- Encrypt transport and managed database/storage at rest; consider field encryption for contact details.
- Restrict admin access; require MFA for operators where possible; audit privileged actions.
- Set API rate limits, request-size limits, account lockout/abuse controls, and model usage budgets. DRF throttling is not a substitute for infrastructure-level abuse protection. [web:199]
- Avoid storing raw AI prompts/responses in application, analytics, error-tracking, or email logs. Redact identifiers and implement retention/deletion.

## 9. Background jobs and reliability

Use Celery for asynchronous mail delivery and scheduled tasks; periodic tasks can be scheduled with Celery Beat or a managed scheduler. [web:202][web:210]

- Store the user's timezone and compute each due date carefully, including daylight-saving changes if applicable.
- Use idempotency keys so duplicate task delivery does not send multiple weekly emails.
- Recheck active consent immediately before sending, not only when scheduling.
- Retry transient provider errors with backoff; stop retrying permanent bounces and expose a delivery status.
- Use a transactional outbox pattern or durable queued event if avoiding dropped notifications is important.
- Do not put sensitive text in task names, queue metadata, or worker logs.

## 10. Repository layout

A monorepo is practical for a student project: separate frontend and backend, with deployment files at root.

```text
student-wellbeing/
  frontend/            # Next.js app
  backend/
    config/            # Django settings, URLs, ASGI/WSGI, Celery
    apps/
      accounts/
      checkins/
      episodes/
      wellbeing/
      safety/
      sharing/
      notifications/
      chat/
      content_admin/
      audit/
    tests/
    manage.py
  infra/               # Compose, deployment, scripts
  .github/workflows/   # tests, image publish, deploy
  docs/                # architecture, API, privacy/safety decisions
  docker-compose.yml
  Dockerfile.backend
  .env.example
  README.md
```

Django config: split base, local, test, and production settings (or environment-driven settings module). Include migrations, requirements lock file, OpenAPI schema, seed command for reviewed content, and management commands for resource verification.

## 11. Tests and quality gates

| Test layer | Examples |
|---|---|
| Unit | Model constraints; date/time logic; consent withdrawal; notification text; helper functions. |
| API integration | Auth required, validation errors, permissions, filtering, pagination, throttling, account export/delete. |
| Privacy / authorization | User A cannot read/update/delete user B's check-in, episode, safety plan, contact, consent, chat, or export. |
| Background tasks | No email without active consent; consent revoked before send; retry/idempotency; bounces; correct timezone. |
| AI safety | Approved knowledge grounding, unsupported question, self-harm scenario, panic, abuse, language mixing, prompt injection, provider outage, rate limits. |
| End-to-end | Sign up → verify → create check-in → see trend → use exercise → opt into email → revoke; SOS review and cancel/send path. |
| Deployment | Container starts, health/readiness probes, migrations, static files, secret config, backup/restore rehearsal. |

Useful tools: pytest + pytest-django, DRF APIClient, factory_boy, Playwright for browser flows, Ruff for Python lint/format, mypy optionally, and coverage reporting. Keep tests deterministic; do not call a paid model in every CI test.

## 12. Deployment and automation

### Recommended deployment pattern

Frontend: Vercel if desired. Django API: a Docker-compatible host with persistent web service. Database: managed PostgreSQL. Redis: managed Redis. Worker and scheduler: separate container processes. Image registry: GitHub Container Registry (GHCR). Vercel documents Django deployment as a Python function; that can suit API workloads, but function/runtime and background-task constraints should be validated for this particular architecture. [web:219][web:220]

### Docker services for local development

- web: Django/Gunicorn or ASGI server.
- worker: Celery worker.
- beat: Celery Beat / scheduled task process.
- db: PostgreSQL for local development.
- redis: queue broker/cache.
- frontend: Next.js development server.

### CI/CD workflow

1. Pull request: install dependencies, lint, type-check, run unit/API/privacy tests, build frontend and backend.
2. Main branch: build tagged backend image, scan dependencies/image, publish to GHCR.
3. Deploy: apply controlled migrations, deploy Django/worker, deploy frontend, run smoke tests.
4. Scheduled checks: exercise/resource review reminders, dependency update PRs, backup/restore verification, helpline link/number checks by human owner.

Image tags: immutable Git commit SHA plus release tag; avoid deploying latest-only. Pin base images and dependency versions. Include a health endpoint and graceful shutdown. Never put secrets in build args or image layers. Django supports production WSGI/ASGI deployment, and Docker documents a Django container workflow. [web:179][web:182]

## 13. Delivery roadmap

| Phase | Deliverable |
|---|---|
| 0. Product definition | Target user, user interviews, scope, safety statement, data inventory, age policy, privacy/legal review plan. |
| 1. Foundation | Repo, Django custom user, PostgreSQL, migrations, API docs, frontend shell, Docker Compose, CI tests. |
| 2. Core wellbeing | Check-ins, episodes, triggers, exercise library, trends, accessibility and localization foundation. |
| 3. Safety and sharing | Safety plan, verified resources, trusted contacts, consent lifecycle, preview/revoke, background email jobs. |
| 4. AI prototype | RAG over vetted content, chat UI, safety layer, usage limits, evaluation set and clinician review. |
| 5. Hardening | Security review, ownership tests, backup/restore, retention/deletion, monitoring and load checks. |
| 6. Deploy | Vercel frontend if selected, Dockerized Django/worker, PostgreSQL/Redis, GHCR, automatic CI/CD, runbook. |

## 14. Definition of done

- A student can create and delete their account and control their own records.
- No cross-user data access is possible in API tests.
- All optional sharing is disabled by default, explicit, understandable, revocable, and verified.
- Weekly task rechecks consent at send time and avoids duplicates.
- SOS messages require an explicit user action and show the exact recipient/content.
- Chatbot clearly identifies itself as AI, uses approved content where appropriate, and has a tested crisis fallback.
- Resource details have an owner and verification date.
- Production secrets are managed securely; debug disabled; backups and deletion behavior are documented.
- Container builds reproducibly, tests run automatically, and an image is published with an immutable tag.
- Project documentation explains limitations and states that the application is not clinical care or emergency monitoring.

## 15. Final recommended scope

For a strong and feasible version, build a modular Django monolith with DRF, PostgreSQL, Next.js, Celery/Redis, a curated RAG chatbot, Docker, and GitHub Actions. Prioritize private check-ins, useful exercises, a user-controlled safety plan, consent-based weekly check-ins, and an explicit SOS flow. Avoid automatic risk alerts, large-scale monitoring, and model training until you have expert oversight, a clear response operation, and an appropriate legal/safeguarding plan.

*This blueprint is an engineering/product plan, not legal or clinical advice. Before real student use—especially for minors—obtain qualified mental-health, safeguarding, and India privacy/legal review.*
