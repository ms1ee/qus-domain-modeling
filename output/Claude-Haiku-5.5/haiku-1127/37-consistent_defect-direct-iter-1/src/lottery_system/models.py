"""Core data models and shared helpers for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

UNRANKED_LEVEL = 1000

_LEVEL_WORDS = {
    "grand": 0,
    "special": 0,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}

_WORD_RE = re.compile(
    r"^\s*(grand|special|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    re.IGNORECASE,
)
_ORDINAL_RE = re.compile(r"^\s*(\d+)(st|nd|rd|th)\b", re.IGNORECASE)


def normalize_text(value: str) -> str:
    """Normalize a name or department for case-insensitive comparison."""
    return " ".join(str(value).split()).casefold()


def prize_level(name: str) -> int:
    """Return the rank of a prize level; smaller numbers mean higher prizes.

    Recognises names starting with words such as "First", "Second", "Third"
    or ordinal numbers such as "1st". Unknown names are ranked last.
    """
    match = _WORD_RE.match(name or "")
    if match:
        return _LEVEL_WORDS[match.group(1).lower()]
    match = _ORDINAL_RE.match(name or "")
    if match:
        return int(match.group(1))
    return UNRANKED_LEVEL


@dataclass(frozen=True)
class User:
    """A lottery participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
