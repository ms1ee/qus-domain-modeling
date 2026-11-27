"""Core data models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NO_LEVEL = 999

_LEVEL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
}


def prize_level_from_name(name: str) -> int:
    """Derive a prize level (1 = highest) from words such as 'First Prize'.

    Prizes without a recognised level word receive a lower priority (NO_LEVEL).
    """
    for word in re.findall(r"[a-z]+", name.lower()):
        if word in _LEVEL_WORDS:
            return _LEVEL_WORDS[word]
    return NO_LEVEL


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery sequence."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        return prize_level_from_name(self.name)


@dataclass
class LotterySession:
    """State of the current lottery event."""

    event_name: str
    status: str = "SETUP"
