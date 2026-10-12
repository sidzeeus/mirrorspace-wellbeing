# Localization

> **NEEDS_HUMAN_REVIEW.** Every translation in this repository other than English is a placeholder written by an engineer. None may be released until a fluent speaker with experience of wellbeing content has reviewed it using the script below (docs/review-needed.md R11). A mistranslated safety sentence can mislead someone at the worst moment.

## How it works

- English is the source language. Text lives in `frontend/messages/en/*.json`, one file per screen.
- A translation is a folder beside it, for example `frontend/messages/hi/`, with files of the same names. It may be partial: any key that is missing falls back to English.
- Adding a language needs translation files and one line in three lists (`LOCALES` in `frontend/src/i18n/request.ts`, `LOCALES` in `frontend/src/components/PreferenceControls.tsx`, `LANGUAGES` in `backend/config/settings/base.py`). No screen code changes.
- The language is chosen in Settings (or in onboarding). The choice is kept in a cookie and on the account, and there is no language in the URL.
- A key beginning with `_` (such as `_review`) is a note for translators and is never shown.
- The unit test `frontend/tests/copy.test.mjs` fails if a translation contains a key that English does not have.

Curated content (exercises, and later the chat knowledge base) is translated separately in the database, one reviewed record per language (`ExerciseTranslation`). An exercise with no approved text in the person's language is shown in English; one with no approved text at all is not shown.

## Current state

| Language | Interface | Exercises | Status |
|---|---|---|---|
| English | Complete | Placeholders | Wording awaiting clinical and legal review |
| Hindi | Partial placeholder: navigation, common buttons, the landing headline, the home greeting, and the key Support sentences | None | Not reviewed. Not for release. |

## Typography for Indian scripts

- Devanagari uses Noto Sans Devanagari, loaded only when it is needed.
- Line height is 1.8 for Hindi, against 1.6 for English, so matras and conjuncts are not clipped.
- Long words may break (`overflow-wrap: anywhere`) rather than overflow or be truncated. Nothing uses an ellipsis to cut text.
- The browser tests load key screens in Hindi at a 320px width with "larger text" on (about 200% of the base layout) and fail if any screen scrolls sideways.

## Review script for a fluent speaker

Give the reviewer a build with the language selected, and this list. They should mark each item pass or fail and write the corrected text beside any failure.

### 1. Meaning and safety

1. Open **Support**. Read every sentence aloud. Does each mean exactly what the English means? Pay special attention to:
   - "This app is not monitored." It must not be readable as "is monitored" or "may be monitored".
   - "The app cannot guarantee that anyone will respond."
   - "If you or someone else is in immediate danger, call your local emergency number."
2. On **Message a trusted person**, read the review screen. Is it unmistakable that nothing has been sent yet? After sending, does the text say "queued" and not "delivered", "sent" or "received"?
3. On the **landing page**, read "What this is not". Is "not therapy", "not a diagnosis" and "not an emergency service" each clear and natural?
4. Anywhere: is there any wording that sounds like a diagnosis, a judgement of the person, a promise of safety, or a command? Note it.

### 2. Tone

5. Does it read as warm, plain and adult? Note anything that sounds clinical, childish, bureaucratic or alarming.
6. Are the button labels verbs that say what will happen ("Save check-in", "Send this message")? Does the same action keep the same name through a flow?
7. Is the register consistent (formal or informal "you")? For Hindi, confirm one of आप or तुम is used throughout, and that it suits students.
8. Are the scale words for mood, energy, stress and sleep natural, evenly spaced, and free of judgement?

### 3. Layout

9. On a small phone, with **Larger text** on, visit: landing, sign in, home, check-in, patterns, exercises, safety plan, Support, sharing, settings. On each: is any text cut off, overlapping, or running off the edge? Are any letters clipped at the top or bottom?
10. Are numbers, dates and times shown in the form readers expect?
11. Do long words wrap in sensible places?

### 4. Screen reader

12. With TalkBack or VoiceOver in that language, complete a check-in and open Support. Is everything announced in the right language, including the slider value and the description of the light?

### Sign-off

| Language | Reviewer | Date | Result | Notes |
|---|---|---|---|---|
| Hindi | | | | |

When a language passes, remove its `_review` notes, update the table in "Current state", and record the sign-off in docs/review-needed.md.
