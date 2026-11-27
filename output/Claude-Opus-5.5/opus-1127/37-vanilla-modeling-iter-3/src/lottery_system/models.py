"""Core data models of the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A participant of the lottery."""
    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
]


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            self.associated_drawer = str(self.associated_drawer).strip() or None

    @property
    def level(self) -> str:
        if " - " in self.name:
            return self.name.split(" - ", 1)[0].strip()
        return self.name

    @property
    def level_rank(self) -> int:
        return prize_level_rank(self.name)

    def rule_description(self) -> str:
        parts = []
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: none")
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}")
        else:
            parts.append("Lottery person: not specified")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)


def prize_level_rank(name: str) -> int:
    """Lower value means higher prize level."""
    level = name.split(" - ", 1)[0].lower() if " - " in name else name.lower()
    for kw, rank in LEVEL_KEYWORDS:
        if kw in level:
            return rank
    return 99
