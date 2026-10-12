# Final review

An independent-style review of the repository against the blueprint's Definition of Done (README Part E, section 14) and the 8 non-negotiables, carried out on 2026-10-12 at commit `6795b18` plus the changes recorded in `docs/progress.md` for that date.

> The reviewer is the same engineer (Claude) who built it. The checks are real and repeatable, but this is not a substitute for an independent audit. Where something has only been shown with a fake provider or on one laptop, it says so.

**Verdict: not ready for real students.** The software does what the specification asks and its safety and privacy rules are enforced by tests. What stands between it and real use is not code: unreviewed clinical, legal and safety wording; unverified helplines with no owner; no real email or AI provider connected; and a pipeline that has never run because the repository has not been pushed anywhere.

## Evidence used

| Check | Result on 2026-10-12 |
|---|---|
| Backend tests (`pytest`, PostgreSQL 16) | 766 passed, 98% coverage |
| Backend lint, format, types, migrations (`ruff`, `mypy`, `makemigrations --check`) | Clean |
| Production configuration (`manage.py check --deploy --fail-level WARNING`) | No issues, on the host and inside the image |
| Browser tests (Playwright with axe, against the production build and real API) | 66 passed (one was flaky on a selector and was fixed) |
| Copy-rule unit tests (`npm run test:unit`) | 7 passed |
| Frontend lint and type-check | Clean |
| Dependency audits (`pip-audit`, `npm audit --omit=dev`) | No known vulnerabilities |
| Staging rehearsal with production images and settings | 18 of 18 smoke tests passed |
| Backup and restore rehearsal | Passed locally |
| Searches of code and copy (below) | No violations found |

## Definition of Done

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | A student can create and delete their account and control their own records. | **PASS** | `apps/accounts/tests/test_registration.py`, `test_deletion.py`; export and deletion coverage by introspection in `tests/test_data_coverage.py`; browser tests `account.spec.ts` and `sharing.spec.ts` ("settings: comfort controls, export and account deletion"). Live run: after deletion, zero owned rows remained. |
| 2 | No cross-user data access is possible in API tests. | **PASS** | `OwnedResourceContract` (`tests/harness.py`) applied to check-ins, episodes, triggers, exercise events, trusted contacts, consents, notifications, chat sessions and chat feedback; `SingletonResourceContract` for the safety plan. `tests/test_harness.py` proves the contract fails on a leaky endpoint. `tests/test_routes.py` enumerates every route and fails if an owned route has no contract test. Extra cases: another person's trigger on an episode, another person's contact in a preview, consent or SOS, another person's chat session. |
| 3 | All optional sharing is disabled by default, explicit, understandable, revocable, and verified. | **PASS** for behaviour. **NEEDS_HUMAN_REVIEW** for "understandable". | Off by default: `TestSharingIsOffByDefault`, browser test "sharing is off by default for a new account". Explicit: `TestGrant::test_every_condition_is_required` (current notice version, preview hash, `confirmed: true`). Revocable: `TestPauseResumeRevoke`. Verified: `TestDoubleOptIn`. The wording a student reads has not been reviewed (review-needed R5, R6). |
| 4 | The weekly task rechecks consent at send time and avoids duplicates. | **PASS** | `apps/notifications/tests/test_delivery.py`: `TestConsentIsCheckedAtSendTime` (revoked, paused, unsubscribed, removed, account closed, suppressed, all between scheduling and sending) and `TestDuplicatesNeverSendTwice`. At scale: `TestWeeklyTaskAtScale`. Live: the planner ran twice and one note was sent. |
| 5 | SOS messages require an explicit user action and show the exact recipient and content. | **PASS** | `apps/sharing/tests/test_sos.py` (`test_sends_exactly_what_was_shown_to_exactly_who_was_shown`, `test_requires_an_explicit_true_confirmation`, `TestNeverAutomatic`); `test_only_the_sos_module_can_create_an_sos_message`; browser tests "SOS send path" and "SOS cancel path". |
| 6 | The chatbot clearly identifies itself as AI, uses approved content where appropriate, and has a tested crisis fallback. | **PASS** with a mocked provider. **NEEDS_HUMAN_REVIEW** before use. | Banner: `chat.spec.ts`, `TestPolicy::test_disclosure_says_it_is_an_ai...`. Approved content only: `TestKnowledge`. Crisis fallback: every crisis case in `apps/chat/evaluation/cases.json` (58 cases) returns the fixed reply and never reaches the model, including when the budget is exhausted or the provider is down. **No real model has been called**, and the phrase list and replies are an engineer's placeholders (R3, R12, R24). |
| 7 | Resource details have an owner and a verification date. | **NEEDS_HUMAN_REVIEW** | The fields, the stale flag, the `flag_stale_resources` command and the weekly reminder exist and are tested (`apps/safety/tests/test_safety.py`). But no owner is assigned (decisions Q7) and both seeded entries are unverified, so production would show an empty helpline list. This blocks launch. |
| 8 | Production secrets are managed securely; debug disabled; backups and deletion behaviour are documented. | **PASS** as built. Not yet exercised on a real host. | Secrets: required from the environment, none in Git or image layers (`test_refuses_to_start_without_required_variables`, `test_no_secret_has_a_usable_default`, release workflow check). Debug off: `test_production_settings_are_locked_down`. Backups and deletion: `docs/runbook.md`, `docs/privacy.md`; rehearsal passed locally. |
| 9 | The container builds reproducibly, tests run automatically, and an image is published with an immutable tag. | **FAIL** | The images build, and were built and run locally tagged `sha-<commit>`. The workflows that run tests and publish to GHCR exist (`.github/workflows/ci.yml`, `release.yml`). But the repository has no remote, so **no workflow has ever run and no image has been published**. Fix: push to GitHub and confirm CI and the release workflow go green. |
| 10 | Project documentation explains limitations and states that the application is not clinical care or emergency monitoring. | **PASS** | `CLAUDE.md`, `docs/privacy.md`, `docs/runbook.md`; in the product: the landing page ("What this is not"), onboarding notice, Support screen, chat banner, every email. The smoke test fails a deploy if the landing page stops saying it. |

## The 8 non-negotiables

| # | Rule | Result | Evidence |
|---|---|---|---|
| 1 | No diagnosis, treatment claims, or promises of suicide prevention. | **PASS** in code. **NEEDS_HUMAN_REVIEW** for all wording. | Search below found none. `frontend/tests/copy.test.mjs`; banned-phrase test on pattern observations (backend and frontend); the chat output check (`policy.violates_policy`) discards replies that diagnose or advise on medication. |
| 2 | All sharing is off by default, explicit, specific, previewable, and revocable. | **PASS** | Definition of Done item 3; the weekly note is limited to four fields by construction (`apps/sharing/weekly.py`) and compared byte for byte in `test_weekly_message.py`. |
| 3 | No automatic risk alerts or trusted-contact notifications from a classifier. | **PASS** | `test_every_crisis_case_never_reaches_the_model_and_alerts_nobody`; `TestNeverAutomatic`; `test_only_the_sos_module_can_create_an_sos_message`; no risk label is stored (`test_no_risk_label_is_stored_about_anyone`). |
| 4 | SOS requires an explicit user action and shows the exact recipient and message first. | **PASS** | Definition of Done item 5. |
| 5 | Never claim the app is monitored, or that an alert was sent, unless true and confirmed. | **PASS** | SOS reply says "queued" only (`test_reply_claims_only_what_is_true`); fixed chat replies (`test_fixed_replies_make_no_false_claims`); copy-rule test "the app never claims to monitor anyone"; delivery status wording. |
| 6 | No sensitive text in logs, task names, queue metadata, Sentry, or analytics. | **PASS** | Canary tests in every app; `TestBackgroundTasks` (ids only); `TestSentryScrubbing`; no analytics exists. Sentry not checked against a live project (security-review S6). |
| 7 | Every user-owned query is filtered by the authenticated user; every such endpoint has a cross-user test. | **PASS** | Definition of Done item 2. |
| 8 | Clinical content, helplines, the crisis workflow and legal copy are placeholders until signed off. | **PASS** as a mechanism. **Nothing is signed off.** | Unreviewed content is hidden unless a development switch is on, and production forces the switch off (`test_unreviewed_content_cannot_be_enabled_in_production`). 39 files carry the `NEEDS_HUMAN_REVIEW` marker; `docs/review-needed.md` lists 24 items and every string on the safety-critical screens. |

## Searches of code and copy

| Looked for | Where | Found |
|---|---|---|
| Diagnosis or treatment claims | All interface messages, email templates, seeded exercises and knowledge, pattern observations | None. Every occurrence is a negation ("not a diagnosis", "cannot diagnose") or a test's banned list. |
| Claims of monitoring or alerts | Interface messages, emails, notices, SOS and chat fixed text | None. The one positive-looking hit is the item "Monitored." under the landing page heading "What this is not". |
| Automatic alerts | Every app, the beat schedule, signals | None. Only `apps/sharing/sos.py`, called from the student's confirmed request, creates an SOS message. |
| Sharing that defaults to on | Models and settings | None. `ChatSession.save_transcript` defaults to `False`; no consent row exists until `grant_weekly_consent` is called; a database constraint stops a non-active consent being scheduled. Observation: `ConsentRecord.status` has a model default of `active`. It is harmless because a row is only ever created by an explicit grant, but removing the default would make that explicit. |
| Sensitive text in logs | Every `logger` call | The only fields logged are `user_id`, `notification_id`, `count`, `task`, `status`, `reason`, `purpose`. No `print` in application code. |
| Missing ownership checks | Every route | None: `tests/test_routes.py`. |
| Placeholder content that could reach production | Exercises, resources, knowledge | Blocked by review status. Seed commands create content as `needs_review`; production cannot show it. Interface wording and email text, however, **are** placeholders that would ship as they are: they carry `_review` notes and are listed in `docs/review-needed.md`, but nothing technical stops them. |
| Secrets in the repository | Tracked files and history | None. No `.env`, key or dump is tracked. |

## Prioritized fix list

### Before any real student uses it (blocking)

1. **Push the repository to GitHub and make CI and the release workflow pass.** Until then Definition of Done item 9 fails, and the browser job has never run on Linux.
2. **Assign the helpline owner and verify every entry** (review-needed R2, decisions Q7). Without it the helpline list is empty in production.
3. **Get the sign-offs in `docs/review-needed.md`**: exercise content, the crisis phrase list and fixed replies, SOS and weekly-note wording, the privacy and consent notices, the age policy, retention periods, and every "not therapy, not monitored" statement.
4. **Connect a real email provider in staging.** Send real invitations, weekly notes and an SOS; trigger a real bounce and a spam complaint; write the provider-specific webhook adapter (R22).
5. **Decide whether chat ships at all in the first release.** The locked MVP cut line (decision D9) puts it after Phases 1 to 3. If it ships: run the evaluation set against the real model with a clinician reading the answers (R24), and review the provider's data terms (R13). If it does not: remove the Chat entry from `frontend/src/app/(app)/more/page.tsx` and leave `CHAT_PROVIDER` on the mock.
6. **Define who responds if a student reports danger** to the team, and write it into the runbook (R14). The app itself must keep saying it is not monitored.
7. **An independent security test.**

### Soon after (important)

8. Multi-factor authentication for the admin, or put it behind an identity-aware proxy (security-review S1).
9. Rate limiting at the edge (S2).
10. A nonce-based script Content-Security-Policy (S3).
11. A management command to re-encrypt existing rows when rotating `FIELD_ENCRYPTION_KEYS` (runbook).
12. Decide how account deletions are re-applied after a database restore (runbook, "Backup and restore").
13. Check Sentry scrubbing against a live project (S6).
14. A real-device pass: a low-end Android phone, TalkBack and VoiceOver (docs/localization.md section 4).

### Later (improvements)

15. Sign-in scores 89 on Lighthouse mobile performance, one under target.
16. Fluent-speaker review and completion of Hindi (R11).
17. Replace the vocabulary-matching embedder with a semantic one, so differently worded questions still find reviewed material.
18. Remove the model-level default on `ConsentRecord.status`.
19. Streamed chat replies; a "sign out everywhere" action (S8).

## Sign-off needed before launch

| Who | What | Reference |
|---|---|---|
| Mental-health professional | Exercise content; pattern observation wording and thresholds; scale wording; chat instructions, knowledge base and evaluation answers | R1, R10, R12, R17, R23, R24 |
| Safeguarding professional | Crisis phrase list and fixed replies; SOS screen and message; weekly-note wording; sharing limits; the human response process; overall safeguarding review | R3, R4, R5, R14, R19, R21 |
| India-qualified privacy lawyer | Privacy and consent notices; the 18+ policy; retention periods including indefinite do-not-email fingerprints and backups; a notice for trusted contacts; provider data terms; breach procedure | R6, R7, R8, R13, R20 |
| Named helpline owner | Every helpline entry, before every release | R2 |
| Fluent speakers | Every non-English string | R11 |
| Security reviewer and owner | Key handling procedure; password and session rules; independent test | R16, R18 |
