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
