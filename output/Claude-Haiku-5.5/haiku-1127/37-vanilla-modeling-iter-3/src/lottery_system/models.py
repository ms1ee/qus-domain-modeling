"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CUSTOM_PRIZE_LEVEL = 99

_LEVEL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}

_LEVEL_PATTERN = re.compile(
    r"\b(first|second|third|fourth|fifth)\s+prize\b", re.IGNORECASE
)


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def prize_level(name: str) -> int:
    """Return the level of a prize derived from its name.

    Lower numbers mean higher prize levels (First Prize = 1).
    Prizes without a recognised level keyword are placed last.
    """
    match = _LEVEL_PATTERN.search(name)
    if not match:
        return CUSTOM_PRIZE_LEVEL
    return _LEVEL_WORDS[match.group(1).lower()]
