# Needs human review

Everything here is a placeholder until a qualified person signs it off. Claude builds the machinery; these decisions and words belong to people with the right expertise.

Nothing on this list may reach real students until its "Signed off by" column is filled in. In code and content these items carry the marker `NEEDS_HUMAN_REVIEW`.

## Standing items

| # | Item | Who should review | Where it will live | Status | Signed off by / date |
|---|---|---|---|---|---|
| R1 | Exercise content (grounding, paced breathing, journaling, planning, movement, wind-down) | Qualified mental-health professional | Exercise seed data, Phase 2 | Not yet written | |
| R2 | Helpline and emergency resource entries, including Tele-MANAS 14416: number, hours, languages, region. Must be re-verified before every release. | Named human owner (unassigned, see Q7 in decisions.md) | Resource seed data, Phase 3 | Not yet written | |
| R3 | Crisis workflow: trigger terms, the fixed safety message, and what is offered | Mental-health and safeguarding professionals | Chat safety module, Phase 4 | Not yet written | |
| R4 | SOS screen wording and the default SOS message text | Safeguarding professional | SOS flow, Phase 3 and Prompt 5d | Not yet written | |
| R5 | Weekly email wording, including the fixed neutral line | Safeguarding professional | Weekly message generator, Phase 3 | Not yet written | |
| R6 | Privacy notice, consent notices and their versions | India-qualified privacy lawyer (DPDP Act and Rules) | Onboarding, sharing flow, `docs/privacy.md` | Not yet written | |
| R7 | Age policy (18+ self-confirmation) and whether it is sufficient | India-qualified privacy lawyer | Registration | Decision D1; mechanism not yet built | |
| R8 | Retention periods: 12-month pseudonymized audit data, chat transcript retention | Privacy lawyer | `docs/privacy.md` | Decision D5; not yet built | |
| R9 | "What this app is and is not" statement and every "not therapy, not monitored" disclaimer | Mental-health professional and lawyer | Landing page, onboarding, SOS, chat | Not yet written | |
| R10 | Pattern observation sentences (correlation-only wording) | Mental-health professional | Patterns endpoint, Phase 2 | Not yet written | |
| R11 | Hindi and any other translations | Fluent speakers with wellbeing-content experience | `next-intl` message files, Prompt 6 | Not yet written | |
| R12 | AI chat system policy, curated knowledge documents, and evaluation-set review | Clinician | Chat app, Phase 4 | Not yet written | |
| R13 | AI and email provider data-processing, retention and training terms | Privacy lawyer | Provider choice (Q1, Q2) | Provider not chosen | |
| R14 | Overall safeguarding review before any real student use | Safeguarding lead | Whole product | Not started | |

## String checklists

Per-screen lists of every string on safety-critical screens are added here as those screens are built (Prompt 5d).
