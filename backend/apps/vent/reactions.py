"""How the figure on the Vent screen reacts to what was written.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R26): the word lists below are placeholders
written by an engineer. A mental-health professional must review them.

This is a mirror, not an assessment. It counts words from short lists and picks the
reaction with the most matches, so the figure can respond in kind: sinking with heavy
words, settling a storm, slowing a racing mind. It does not understand the text, it
stores nothing, and it never contacts anyone.

Crisis wording is checked first, with the same code the chat uses
(`apps.chat.safety.assess`), and always wins: the figure stays steady and the screen
offers Support, the safety plan and helplines. Nobody is told (non-negotiable 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.chat import safety

# In order of precedence when two reactions match equally often.
REACTIONS = ("steady", "heavy", "racing", "storm", "alone", "lighter", "listening")

# fmt: off
_WORDS: dict[str, tuple[str, ...]] = {
    "heavy": (
        "sad", "sadness", "tired", "exhausted", "drained", "empty", "numb", "cry", "crying",
        "cried", "tears", "hopeless", "worthless", "useless", "miserable", "depressed", "low",
        "down", "heartbroken", "broken", "hurt", "hurts", "grief", "lost", "failure", "failed",
        "pointless", "heavy", "dukhi", "udaas", "udas", "thak", "thaka", "thaki", "rona", "dukh",
    ),
    "racing": (
        "anxious", "anxiety", "nervous", "worried", "worry", "worrying", "scared", "afraid",
        "fear", "overthinking", "overthink", "stressed", "stress", "overwhelmed", "pressure",
        "tense", "restless", "deadline", "deadlines", "exam", "exams", "dread", "uneasy",
        "tension", "dar", "darr", "chinta", "pareshan",
    ),
    "storm": (
        "angry", "anger", "furious", "mad", "rage", "hate", "annoyed", "irritated", "frustrated",
        "frustrating", "unfair", "pissed", "sick of", "fed up", "betrayed", "resent", "gussa",
        "naraz", "chid",
    ),
    "alone": (
        "lonely", "alone", "isolated", "ignored", "left out", "nobody", "no one", "invisible",
        "unwanted", "abandoned", "miss", "missing", "homesick", "friendless", "akela", "akeli",
        "koi nahi", "tanha",
    ),
    "lighter": (
        "better", "relieved", "relief", "grateful", "thankful", "hopeful", "hope", "calm",
        "calmer", "lighter", "proud", "happy", "glad", "okay", "peaceful", "good", "accha",
        "achha", "khush", "sukoon",
    ),
}
# fmt: on

_NEGATION = re.compile(r"\b(not|no|never|dont|didnt|isnt|wasnt|cant|nahi|nahin|na)\s+(\w+\s+)?$")


def _pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(phrase)}\b")


_PATTERNS = {kind: [_pattern(w) for w in words] for kind, words in _WORDS.items()}


@dataclass(frozen=True)
class Reaction:
    kind: str
    #: "crisis", "distress" or None. Returned to the screen, never stored.
    level: str | None = None


def _count(kind: str, text: str) -> int:
    total = 0
    for pattern in _PATTERNS[kind]:
        for match in pattern.finditer(text):
            negated = _NEGATION.search(text[: match.start()][-24:])
            if kind == "lighter" and negated:
                # "not okay", "not hopeful": the opposite of lighter.
                continue
            total += 1
    return total


def react(text: str) -> Reaction:
    assessment = safety.assess(text)
    if assessment.level == safety.CRISIS:
        return Reaction("steady", safety.CRISIS)
    if assessment.level == safety.DISTRESS:
        return Reaction("racing", safety.DISTRESS)

    cleaned = safety.normalize(text)
    scores = {kind: _count(kind, cleaned) for kind in _WORDS}
    best = max(scores.values())
    if best == 0:
        return Reaction("listening")
    for kind in REACTIONS:
        if scores.get(kind) == best:
            return Reaction(kind)
    return Reaction("listening")
