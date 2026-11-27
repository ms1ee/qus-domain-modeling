"""Core data models of the lottery system."""

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
    """A prize configuration (one lottery round)."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [g for g in self.avoid_groups if g and str(g).strip()]
        if isinstance(self.associated_drawer, str):
            drawer = self.associated_drawer.strip()
            self.associated_drawer = drawer or None


_LEVEL_PATTERNS = [
    (r"\b(grand|special|super)\b", 0),
    (r"\bfirst\b|\b1st\b", 1),
    (r"\bsecond\b|\b2nd\b", 2),
    (r"\bthird\b|\b3rd\b", 3),
    (r"\bfourth\b|\b4th\b", 4),
    (r"\bfifth\b|\b5th\b", 5),
    (r"\b(consolation|participation|lucky)\b", 50),
]


def prize_rank(name: str) -> int:
    """Return a rank for a prize name; smaller means higher prize level."""
    lowered = (name or "").lower()
    for pattern, rank in _LEVEL_PATTERNS:
        if re.search(pattern, lowered):
            return rank
    return 99


def normalize(text: Optional[str]) -> str:
    """Normalize a text for case/space-insensitive comparison."""
    if not text:
        return ""
    return " ".join(str(text).split()).lower()
