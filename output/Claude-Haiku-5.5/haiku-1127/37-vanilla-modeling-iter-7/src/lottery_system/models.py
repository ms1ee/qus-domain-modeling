"""Core data models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LEVEL_PATTERN = re.compile(r"^\s*(First|Second|Third)\b", re.IGNORECASE)
_LEVEL_VALUES = {"first": 1, "second": 2, "third": 3}
_UNRANKED_LEVEL = 4


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery library.

    avoid_groups: department groups whose members are excluded for this prize.
    associated_drawer: the lottery person who draws this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        """Prize level derived from the name: First=1 (highest) ... others=4."""
        match = _LEVEL_PATTERN.match(self.name)
        if match:
            return _LEVEL_VALUES[match.group(1).lower()]
        return _UNRANKED_LEVEL
