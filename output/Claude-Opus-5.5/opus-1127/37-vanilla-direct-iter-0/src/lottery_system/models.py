"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class User:
    """A participant of the lottery."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer or None

    def __str__(self) -> str:
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "Not specified"
        return (f"{self.name} | Quantity: {self.quantity} | "
                f"Lottery person: {drawer} | Avoidance groups: {avoid}")


_LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("sixth", 6),
]

UNRANKED_LEVEL = 99


def prize_level(name: str) -> int:
    """Return the level of a prize: smaller numbers mean higher prizes.

    Prizes whose names do not contain a recognised level keyword are
    considered lower than all ranked prizes.
    """
    lower = (name or "").lower()
    for keyword, level in _LEVEL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lower):
            return level
    return UNRANKED_LEVEL
