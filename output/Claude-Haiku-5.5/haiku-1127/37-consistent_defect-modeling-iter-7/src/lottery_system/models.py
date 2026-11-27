"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


def normalize(text: str) -> str:
    """Return a canonical form of a name or group for case-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


@dataclass
class User:
    """A participant in the team building lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        """Prize level derived from the prize name (1 = highest).

        "First", "Second" and "Third" map to levels 1, 2 and 3.
        Custom prizes without a recognised level keyword get a large value so
        they are listed after the standard prize levels.
        """
        match = re.search(r"\b(first|second|third)\b", self.name, re.IGNORECASE)
        if not match:
            return 999
        return {"first": 1, "second": 2, "third": 3}[match.group(1).lower()]
