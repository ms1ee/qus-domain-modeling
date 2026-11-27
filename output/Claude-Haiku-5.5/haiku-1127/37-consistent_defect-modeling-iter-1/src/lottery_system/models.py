"""Domain models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CUSTOM_PRIZE_LEVEL = 99

_LEVEL_PATTERNS = [
    (re.compile(r"\bfirst\b", re.IGNORECASE), 1),
    (re.compile(r"\bsecond\b", re.IGNORECASE), 2),
    (re.compile(r"\bthird\b", re.IGNORECASE), 3),
]


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round.

    avoid_groups: department groups whose members are drawn after other members.
    associated_drawer: the lottery person associated with this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        """Prize level derived from the name: 1 = highest. Custom prizes rank last."""
        for pattern, value in _LEVEL_PATTERNS:
            if pattern.search(self.name):
                return value
        return CUSTOM_PRIZE_LEVEL

    @property
    def is_custom(self) -> bool:
        return self.level == CUSTOM_PRIZE_LEVEL


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Return prizes ordered from the highest level to the lowest (stable)."""
    return sorted(prizes, key=lambda prize: prize.level)
