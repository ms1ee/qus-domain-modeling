"""Core data models for the lottery system."""

from __future__ import annotations

import re
from typing import List, Optional


class User:
    """A participant of the lottery."""

    def __init__(self, name, department):
        self.name = str(name).strip() if name is not None else ""
        self.department = str(department).strip() if department is not None else ""

    @property
    def is_valid(self) -> bool:
        return bool(self.name) and bool(self.department)

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.name == other.name and self.department == other.department

    def __hash__(self):
        return hash((self.name, self.department))

    def __repr__(self):
        return f"User(name={self.name!r}, department={self.department!r})"

    def __str__(self):
        return f"{self.name} ({self.department})"


class Prize:
    """A prize to be drawn in one lottery round."""

    def __init__(self, name, quantity, avoid_groups: Optional[List[str]] = None,
                 associated_drawer: Optional[str] = None):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups = [str(g).strip() for g in (avoid_groups or []) if str(g).strip()]
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else associated_drawer
        self.associated_drawer = drawer or None

    @property
    def level_rank(self) -> int:
        return prize_level_rank(self.name)

    def __eq__(self, other):
        if not isinstance(other, Prize):
            return NotImplemented
        return (self.name == other.name and self.quantity == other.quantity
                and self.avoid_groups == other.avoid_groups
                and self.associated_drawer == other.associated_drawer)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return (f"Prize(name={self.name!r}, quantity={self.quantity}, "
                f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})")


_LEVEL_KEYWORDS = [
    (r"\b(special|grand)\b", 0),
    (r"\bfirst\b", 1),
    (r"\bsecond\b", 2),
    (r"\bthird\b", 3),
    (r"\bfourth\b", 4),
    (r"\bfifth\b", 5),
    (r"\b(consolation|participation|lucky)\b", 6),
]


def prize_level_rank(name: str) -> int:
    """Return a numeric level rank (smaller = higher level). Unknown -> 50."""
    lower = (name or "").lower()
    for pattern, rank in _LEVEL_KEYWORDS:
        if re.search(pattern, lower):
            return rank
    return 50
