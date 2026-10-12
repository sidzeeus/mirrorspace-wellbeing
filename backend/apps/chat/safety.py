"""The crisis workflow for chat. Deterministic code, not a prompt.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R3): the phrase lists and the fixed replies
below are placeholders written by an engineer. A mental-health and a safeguarding
professional must review them, and must measure false positives and false negatives on
real-world wording, before any student uses the chat.

How it works:

- `assess` runs on every student message BEFORE anything is sent to the AI provider,
  and again on the model's reply AFTER it comes back.
- If it finds wording that suggests a crisis, routine conversation stops. The student
  gets a fixed reply written by people, with routes to their own safety plan, checked
  helplines and their trusted contacts. The AI is not asked to handle it.
- This check never contacts anyone. Non-negotiable 3: no alert, message or record is
  sent to a trusted contact, a staff member or anyone else because of what it finds.
  The replies never say the app is monitored or that someone has been told.

It is a wide net on purpose: a false alarm shows a calm message with options; a miss
would send a crisis message to a language model. It is not a risk assessment, and no
"risk level" is stored about anyone.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CRISIS = "crisis"
DISTRESS = "distress"

_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)


_DEVANAGARI = (chr(0x0900), chr(0x097F))


def normalize(text: str) -> str:
    """Lower-case, strip accents and punctuation, undo simple obfuscation."""
    text = unicodedata.normalize("NFKD", text.lower())
    # Strip accents from Latin letters only. In Devanagari the "combining" marks are
    # part of the spelling (the virama joins consonants), so they are kept.
    text = "".join(
        ch for ch in text if not unicodedata.combining(ch) or _DEVANAGARI[0] <= ch <= _DEVANAGARI[1]
    )
    text = text.translate(_LEET)
    # "don't" becomes "dont", not "don t".
    text = re.sub("['’`]", "", text)
    text = re.sub(r"[^a-zऀ-ॿ\s]", " ", text)
    # "killlll" -> "kill", "sooo" -> "so": runs of 3+ letters collapse to one.
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


# Each pattern is matched against the normalized text. Optional letters and loose gaps
# cover common misspellings; romanized Hindi and Devanagari cover code-switching.
_CRISIS_PATTERNS = [
    # Self-harm and suicide, English
    r"\bsu+i*[cs]+i+d",  # suicide, sucide, suiside, suicidal
    r"\bkil+(ing)? (my ?self|me)\b",
    r"\bkms\b",
    r"\b(kil+|hurt|harm|cut) your ?self\b",
    r"\bend(ing)? your (own )?life\b",
    r"\byou should (just )?die\b",
    r"\bunalive\b",
    r"\bend(ing)? (my|this) life\b",
    r"\bend it al+\b",
    r"\btake my (own )?life\b",
    r"\b(want|wanna|wish|going|gonna|ready) (to )?(die|be dead|disappear forever)\b",
    r"\bwish i (was|were) dead\b",
    r"\bbet+er of+ dead\b",
    r"\b(no|not any|dont have a) reason to live\b",
    r"\b(dont|do not|cant|can not|cannot) (want to )?(live|go on|be here|exist)( any ?more| any longer)?\b",
    r"\bself ?harm",
    r"\b(cut|cutting|hurt|hurting|harm|harming|burn|burning) my ?self\b",
    r"\bover ?dos",
    r"\bjump of+\b",
    r"\bhang(ing)? my ?self\b",
    # Self-harm and suicide, romanized Hindi and Devanagari
    r"\bkhud ?ku?shi\b",
    r"\batma ?hat+ya\b",
    r"\b(marna|mar jana|mar jaun|mar jau|jaan dena|jaan de du) ?(chahta|chahti|chahiye|hai|hu|hun|hoon)?\b",
    r"\bje+na nahi+ (chahta|chahti|hai)\b",
    r"\bzindagi khatam\b",
    r"आत्महत्या",
    r"खुदकुशी",
    r"मरना चाहत",
    r"जीना नहीं चाहत",
    # Being harmed by someone, or immediate danger
    r"\b(he|she|they|my \w+) (hit|hits|beat|beats|hurt|hurts|rape[sd]?|molest\w*|abuse[sd]?) me\b",
    r"\b(being|been|am|was|got|getting) (abuse[sd]|rape[sd]|molested|assaulted|beaten|stalked|threatened)\b",
    r"\bsexual+y (abuse[sd]|assaulted|harassed)\b",
    r"\b(force[sd]?|forcing) (me|himself|herself)\b",
    r"\bnot safe at home\b",
    r"\bafraid (he|she|they) (will|wil|might) (kil+|hurt) me\b",
    r"\b(mujhe|mujhko) (marta|maarta|peet+a|maarte) (hai|hain)\b",
    # Harming someone else
    r"\b(kil+|hurt|stab|shoot) (him|her|them|someone|somebody|my \w+)\b",
]
_DISTRESS_PATTERNS = [
    r"\bpanic(k)?ing\b",
    r"\bpanic at+ack",
    r"\bcant breath",
    r"\bcan not breath",
    r"\bheart is (racing|pounding)\b",
    r"\b(im|i am|feel like im) (going to|gonna) (pass out|faint)\b",
    r"\bfreaking out\b",
    r"\bghabrahat\b",
    r"\bsaans nahi+ aa\b",
    r"घबराहट",
]

_CRISIS_RE = [re.compile(pattern) for pattern in _CRISIS_PATTERNS]
_DISTRESS_RE = [re.compile(pattern) for pattern in _DISTRESS_PATTERNS]

# Phrases that mention a crisis word without being about the person, e.g. coursework.
# Kept very short on purpose: when in doubt, the fixed reply is shown.
_NOT_ABOUT_SELF = re.compile(
    r"\b(essay|assignment|lecture|exam question|novel|film|movie) (on|about)\b"
)


@dataclass(frozen=True)
class Assessment:
    """`level` is None, "distress" or "crisis". Never stored against a person."""

    level: str | None

    @property
    def triggered(self) -> bool:
        return self.level is not None


def assess(text: str) -> Assessment:
    cleaned = normalize(text)
    if any(pattern.search(cleaned) for pattern in _CRISIS_RE):
        if _NOT_ABOUT_SELF.search(cleaned) and not re.search(r"\b(i|me|my|myself)\b", cleaned):
            return Assessment(None)
        return Assessment(CRISIS)
    if any(pattern.search(cleaned) for pattern in _DISTRESS_RE):
        return Assessment(DISTRESS)
    return Assessment(None)


# --- Fixed replies, written by people (placeholders pending review) ---------------

CRISIS_REPLY = (
    "I am an AI, and this sounds like more than I can help with safely. I am not able "
    "to respond to an emergency, and nobody is told about this conversation.\n\n"
    "You do not have to handle this alone. From Support you can open your own safety "
    "plan, call a helpline, or send a message to someone you trust. If you or someone "
    "else is in immediate danger, call your local emergency number now."
)
DISTRESS_REPLY = (
    "That sounds really intense. I am an AI, so I cannot be with you in this, but there "
    "are things you can reach right now.\n\n"
    "From Support you can start a slow-breathing exercise, open your safety plan, or "
    "contact someone you trust. If it feels like an emergency, call your local "
    "emergency number."
)

FIXED_REPLIES = {CRISIS: CRISIS_REPLY, DISTRESS: DISTRESS_REPLY}

# What the screen offers under a fixed reply. All are things the student does; none
# happens by itself.
ACTIONS = [
    {"type": "support", "href": "/support"},
    {"type": "safety_plan", "href": "/support#plan"},
    {"type": "helplines", "href": "/support#call"},
    {"type": "trusted_contact", "href": "/support#message"},
]
