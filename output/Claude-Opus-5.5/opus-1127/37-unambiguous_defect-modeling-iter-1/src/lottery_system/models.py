"""Core data models of the lottery system."""

from __future__ import annotations

import re
from typing import List, Optional


def normalize(text: Optional[str]) -> str:
    """Normalize a name / group string for comparisons."""
    if text is None:
        return ""
    return " ".join(str(text).strip().split()).casefold()


class User:
    """A participant of the lottery (name + department group)."""

    def __init__(self, name: str, department: str):
        self.name = str(name).strip()
        self.department = str(department).strip()
        self.is_valid = True

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


_LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("1st", 1),
    ("second", 2),
    ("2nd", 2),
    ("third", 3),
    ("3rd", 3),
    ("fourth", 4),
    ("4th", 4),
    ("fifth", 5),
    ("5th", 5),
]

UNKNOWN_LEVEL_RANK = 100


def prize_level_rank(name: str) -> int:
    """Return the prize level rank derived from its name (lower = higher level)."""
    low = normalize(name)
    for keyword, rank in _LEVEL_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", low):
            return rank
    return UNKNOWN_LEVEL_RANK


class Prize:
    """A prize to be drawn in one lottery round."""

    def __init__(self, name: str, quantity: int, avoid_groups: Optional[List[str]] = None,
                 associated_drawer: Optional[str] = None):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups = list(avoid_groups) if avoid_groups else []
        if associated_drawer is not None:
            associated_drawer = str(associated_drawer).strip() or None
        self.associated_drawer = associated_drawer

    @property
    def level(self) -> int:
        return prize_level_rank(self.name)

    def avoids(self, department: str) -> bool:
        dep = normalize(department)
        return any(normalize(g) == dep for g in self.avoid_groups)

    def rule_description(self) -> str:
        parts = []
        if self.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("No avoidance groups")
        parts.append("Drawer: " + (self.associated_drawer or "N/A"))
        parts.append("Previous winners excluded")
        return "; ".join(parts)

    def __repr__(self):
        return (f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
                f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})")
