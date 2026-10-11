"""Versioned notices and fixed wording for sharing.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R4, R5, R6): every string in this file is
placeholder wording. A privacy lawyer and a safeguarding professional must review it.

Changing any wording that a student agrees to means bumping the matching version. A
consent records the version the student saw, and a consent request that quotes an old
version is refused.
"""

from __future__ import annotations

PRIVACY_NOTICE_VERSION = "2026-10-placeholder-1"
WEEKLY_NOTICE_VERSION = "2026-10-placeholder-1"
SOS_TEMPLATE_VERSION = "2026-10-placeholder-1"

# The one fixed line in every weekly note (decision D3). It is never personalised.
WEEKLY_NEUTRAL_LINE = "This is a routine weekly note. Silence does not mean anything either way."

# What the student is told before turning the weekly note on.
WEEKLY_NOTICE = {
    "purpose": (
        "Send one short note a week to a person you chose, so they know you are still "
        "using this app."
    ),
    "shared": [
        "Your display name",
        "The dates of the week covered",
        "How many of those 7 days you checked in",
        "One fixed line that is the same for everyone",
    ],
    "never_shared": [
        "Mood, sleep, energy or stress values",
        "Episodes, triggers or what helped",
        "Your safety plan",
        "Chats",
        "Any assessment of how you are doing",
    ],
    "limits": [
        "Nobody monitors these notes, and the app does not act on them.",
        "A missed note or a quiet week does not mean anything about your safety.",
        "The note is paused automatically if you do not confirm it every 90 days.",
    ],
    "control": "You can pause or stop this at any time. The person can also unsubscribe.",
}

UNSUBSCRIBE_PREVIEW_LINE = "To stop receiving these messages: [a personal unsubscribe link]"
