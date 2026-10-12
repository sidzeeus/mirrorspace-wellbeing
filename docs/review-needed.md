# Needs human review

Everything here is a placeholder until a qualified person signs it off. Claude builds the machinery; these decisions and words belong to people with the right expertise.

Nothing on this list may reach real students until its "Signed off by" column is filled in. In code and content these items carry the marker `NEEDS_HUMAN_REVIEW`.

## Standing items

| # | Item | Who should review | Where it will live | Status | Signed off by / date |
|---|---|---|---|---|---|
| R1 | Exercise content (grounding, paced breathing, journaling, planning, movement, wind-down) | Qualified mental-health professional | `backend/apps/wellbeing/seed/exercises.json` (6 placeholders, loaded as `needs_review`) | Placeholder written in Phase 2 | |
| R2 | Helpline and emergency resource entries, including Tele-MANAS 14416: number, hours, languages, region. Must be re-verified before every release. | Named human owner (unassigned, see Q7 in decisions.md) | `backend/apps/safety/seed/resources.json` (Tele-MANAS 14416 and 112, both unverified, hidden until approved). Check with `python manage.py flag_stale_resources` | Placeholder written in Phase 3 | |
| R3 | Crisis workflow: trigger terms, the fixed safety message, and what is offered | Mental-health and safeguarding professionals | Chat safety module, Phase 4 | Not yet written | |
| R4 | SOS screen wording and the default SOS message text | Safeguarding professional | `SOS_SUBJECT`, `SOS_BODY` in `backend/apps/sharing/sos.py`; reply and limit wording in `apps/sharing/views.py` | Placeholder written in Phase 3 | |
| R5 | Weekly email wording, including the fixed neutral line | Safeguarding professional | `WEEKLY_SUBJECT`, `WEEKLY_BODY` in `backend/apps/sharing/weekly.py`; `WEEKLY_NEUTRAL_LINE` and `WEEKLY_NOTICE` in `apps/sharing/notices.py` | Placeholder written in Phase 3 | |
| R6 | Privacy notice, consent notices and their versions | India-qualified privacy lawyer (DPDP Act and Rules) | `docs/privacy.md` (engineering description); notice versions in `backend/apps/sharing/notices.py` | Engineering description written in Phase 3; student-facing notices not yet written | |
| R7 | Age policy (18+ self-confirmation) and whether it is sufficient | India-qualified privacy lawyer | Registration (`RegisterSerializer.validate_age_confirmed`) | Self-confirmation checkbox built in Phase 1 | |
| R8 | Retention periods: 12-month pseudonymized audit data, chat transcript retention | Privacy lawyer | `docs/privacy.md` "Retention and deletion"; also the indefinite do-not-email fingerprints (B36) | Built in Phase 3 | |
| R9 | "What this app is and is not" statement and every "not therapy, not monitored" disclaimer | Mental-health professional and lawyer | Landing page, onboarding, SOS, chat | Not yet written | |
| R10 | Pattern observation sentences (correlation-only wording) | Mental-health professional | `OBSERVATION_TEMPLATES` and `NOTE` in `backend/apps/checkins/patterns.py`; also the thresholds in B19 | Placeholder written in Phase 2 | |
| R11 | Hindi and any other translations | Fluent speakers with wellbeing-content experience | `next-intl` message files, Prompt 6 | Not yet written | |
| R12 | AI chat system policy, curated knowledge documents, and evaluation-set review | Clinician | Chat app, Phase 4 | Not yet written | |
| R13 | AI and email provider data-processing, retention and training terms | Privacy lawyer | Provider choice (Q1, Q2) | Provider not chosen | |
| R14 | Overall safeguarding review before any real student use | Safeguarding lead | Whole product | Not started | |
| R15 | Account email wording (confirm email, password reset, "you already have an account"), including the line "It is not therapy and it is not monitored by anyone." | Lawyer for the disclaimer; owner for tone | `backend/apps/accounts/templates/accounts/email/` | Placeholder written in Phase 1 | |
| R16 | Password rules (10+ characters, common-password check) and the 7-day idle session timeout | Owner / security reviewer | `backend/config/settings/base.py` | Built in Phase 1 | |
| R17 | The 1 to 5 scales and their meaning (what "1" and "5" say on screen), and the 7-day back-dating window | Mental-health professional | `backend/apps/checkins/models.py`, check-in screen (Prompt 5b) | Built in Phase 2; labels not yet written | |
| R18 | Field-encryption key handling: generation, backup, rotation procedure | Security reviewer / owner | `backend/config/fields.py`, runbook (Phase 6) | Mechanism built in Phase 2; procedure not yet written | |
| R19 | Invitation email to a trusted contact, and the text shown on the accept/decline and unsubscribe pages | Safeguarding professional and lawyer | `INVITATION_SUBJECT`, `INVITATION_BODY` in `backend/apps/notifications/render.py`; `InvitationView` in `apps/sharing/views.py` | Placeholder written in Phase 3 | |
| R20 | Whether trusted contacts need their own privacy notice (their name and email are stored at the student's request) | India-qualified privacy lawyer | `docs/privacy.md` "Open items" | Open | |
| R21 | Safeguarding review of the sharing rules: 3 contacts, 90-day re-confirmation, SOS limits (3 an hour, 6 a day), fixed SOS text | Safeguarding lead | decisions B22, B25, B29, B30 | Built in Phase 3 | |
| R22 | The email provider's bounce/complaint webhook mapping, once a provider is chosen | Engineer + owner | `backend/apps/notifications/views.py` `EmailWebhookView` | Generic endpoint built; provider adapter not written | |

## String checklists

Per-screen lists of every string on safety-critical screens are added here as those screens are built (Prompt 5d).

<!-- string-checklist:start -->
NEEDS_HUMAN_REVIEW. Generated by `frontend/scripts/string-checklist.mjs`. Do not edit by hand; edit the message file and run the script.

### Support (SOS) screen (`frontend/messages/en/support.json`)

| Key | Text | Reviewed by / date |
|---|---|---|
| `title` | Support | |
| `close` | Close support | |
| `intro` | Four things you can do right now. Take your time. | |
| `limits` | This app is not monitored. Nobody is told that you opened this screen, and the app cannot guarantee that anyone will respond. | |
| `emergency` | If you or someone else is in immediate danger, call your local emergency number. | |
| `offline` | You are offline. Your saved plan and helplines are still here. Sending a message needs a connection. | |
| `menu` | Support options | |
| `options.calm` | A calming exercise | |
| `options.calmHint` | Slow breathing, at your own pace. | |
| `options.plan` | My safety plan | |
| `options.planHint` | What you wrote for moments like this. | |
| `options.message` | Message a trusted person | |
| `options.messageHint` | You see the exact message before anything is sent. | |
| `options.call` | Call a helpline | |
| `options.callHint` | Numbers a person has checked. | |
| `calm.title` | A calming exercise | |
| `calm.body` | Breathe in for four, out for six. Stop whenever you like. | |
| `plan.title` | My safety plan | |
| `plan.warning_signs` | My warning signs | |
| `plan.coping_steps` | Things I can do | |
| `plan.people` | People I can reach | |
| `plan.empty` | You have not written a plan yet. You can write one when things are calmer. | |
| `plan.write` | Write my plan | |
| `plan.edit` | Edit my plan | |
| `plan.signIn` | Sign in to see your plan. | |
| `plan.saved` | This is the copy saved on this device on {date}. | |
| `plan.unavailable` | Your plan could not be loaded, and there is no saved copy on this device. | |
| `message.title` | Message a trusted person | |
| `message.intro` | Choose a person. You will see exactly who the message goes to and exactly what it says before anything is sent. | |
| `message.signIn` | Sign in to message a trusted person. | |
| `message.needsConnection` | Sending a message needs a connection. You can still call a helpline below. | |
| `message.none` | Nobody has agreed to receive messages from you yet. You can invite someone in Sharing. | |
| `message.setUp` | Open Sharing | |
| `message.choose` | Message {name} | |
| `message.reviewTitle` | Review before sending | |
| `message.to` | To | |
| `message.subject` | Subject | |
| `message.text` | Message | |
| `message.notReceiving` | This person has not agreed to receive messages, so this cannot be sent. | |
| `message.send` | Send this message | |
| `message.cancel` | Do not send | |
| `message.cancelled` | Nothing was sent. | |
| `message.sending` | Sending | |
| `message.queuedTitle` | Queued to send | |
| `message.status` | Delivery status is in Sharing. | |
| `message.another` | Back to support options | |
| `call.title` | Call a helpline | |
| `call.saved` | This is the list saved on this device on {date}. | |
| `call.empty` | No checked helplines are listed yet. If you are in immediate danger, call your local emergency number. | |
| `call.unavailable` | The helpline list could not be loaded, and there is no saved copy on this device. | |
| `top` | Back to the top | |

### Safety plan screen (`frontend/messages/en/plan.json`)

| Key | Text | Reviewed by / date |
|---|---|---|
| `title` | My safety plan | |
| `intro` | Your own words for hard moments. Only you can see it. It is saved on this device too, so it opens without a connection. | |
| `private` | Encrypted, never shared, and never sent to anyone. | |
| `warning_signs` | My warning signs | |
| `warning_signsHint` | What you notice in yourself when things are getting hard. One per line. | |
| `coping_steps` | Things I can do | |
| `coping_stepsHint` | Small things that have helped before. One per line. | |
| `people` | People I can reach | |
| `peopleHint` | Names, and numbers if you like. One per line. | |
| `resources` | Helplines to keep in my plan | |
| `resourcesNone` | No checked helplines are available to add yet. | |
| `limit` | Up to 12 lines, each up to 200 characters. | |
| `save` | Save plan | |
| `saved` | Plan saved. | |
| `edit` | Edit plan | |
| `cancel` | Stop editing | |
| `print` | Print | |
| `empty` | Nothing written yet. A few lines now can help later. | |
| `start` | Write my plan | |
| `emptySection` | Nothing here yet. | |
| `updated` | Last changed {date} | |
| `offlineCopy` | You are offline. This is the copy saved on this device on {date}. Editing needs a connection. | |
| `delete` | Delete my plan | |
| `deleteConfirm` | Delete the whole plan? This cannot be undone. | |
| `deleteYes` | Delete plan | |
| `deleteNo` | Keep plan | |
| `error` | Your plan could not be loaded. | |

### Helplines screen (`frontend/messages/en/resources.json`)

| Key | Text | Reviewed by / date |
|---|---|---|
| `title` | Helplines and services | |
| `intro` | These services are run by other organisations, not by this app. Each entry shows the date a person last checked its details. | |
| `emergency` | If you or someone else is in immediate danger, call your local emergency number. | |
| `empty` | No checked helplines are listed yet. Entries appear here once a person has verified each number. | |
| `unavailable` | The helpline list could not be loaded. Check your connection and try again. | |
| `offlineCopy` | You are offline. This is the list saved on this device on {date}. | |
| `call` | Call {phone} | |
| `callLabel` | Call {name} on {phone} | |
| `website` | Open the website of {name} | |
| `websiteShort` | Website | |
| `region` | Region | |
| `languages` | Languages | |
| `hours` | Hours | |
| `verified` | Checked on {date} | |
| `never` | Not checked yet | |
| `stale` | This entry has not been checked recently. The details may have changed. | |
| `types.helpline` | Helpline | |
| `types.emergency` | Emergency service | |
| `types.text_line` | Text or chat line | |
| `types.campus` | Campus service | |
| `types.online` | Online resource | |

### Offline fallback screen (`frontend/messages/en/offline.json`)

| Key | Text | Reviewed by / date |
|---|---|---|
| `title` | You are offline | |
| `body` | This page was not saved on this device. Support, your saved safety plan and the helpline list still work without a connection. | |
| `support` | Open support | |
| `helplines` | Helplines | |
| `retry` | Try the home screen again | |

<!-- string-checklist:end -->
