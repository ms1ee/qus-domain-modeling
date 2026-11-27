"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


def normalize_name(value: Optional[str]) -> str:
    """Normalize a name for comparison: trimmed, single-spaced, lowercase."""
    if value is None:
        return ""
    return " ".join(str(value).split()).lower()


@dataclass
class User:
    """A lottery participant."""

    name: str
    department: str

    def __post_init__(self) -> None:
        self.name = " ".join(str(self.name).split())
        self.department = " ".join(str(self.department).split())

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
        self.name = " ".join(str(self.name).split())
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [
                " ".join(str(g).split()) for g in self.avoid_groups if str(g).strip()
            ]
        if self.associated_drawer is not None:
            drawer = " ".join(str(self.associated_drawer).split())
            self.associated_drawer = drawer or None

    @property
    def level_rank(self) -> int:
        return prize_level_rank(self.name)

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity}"


_LEVEL_PATTERNS = [
    (r"\b(special|grand|super)\b", 0),
    (r"\bfirst\b|\b1st\b", 1),
    (r"\bsecond\b|\b2nd\b", 2),
    (r"\bthird\b|\b3rd\b", 3),
    (r"\bfourth\b|\b4th\b", 4),
    (r"\bfifth\b|\b5th\b", 5),
    (r"\b(participation|consolation|lucky)\b", 50),
]


def prize_level_rank(prize_name: str) -> int:
    """Return a rank for the prize level (smaller = higher level)."""
    lowered = (prize_name or "").lower()
    for pattern, rank in _LEVEL_PATTERNS:
        if re.search(pattern, lowered):
            return rank
    return 99
