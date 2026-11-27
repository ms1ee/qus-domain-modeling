"""Core data models of the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Prize level keywords, ordered from the highest level to the lowest.
_LEVEL_KEYWORDS = [
    (0, "Special Prize", ("special", "grand", "特等")),
    (1, "First Prize", ("first", "一等")),
    (2, "Second Prize", ("second", "二等")),
    (3, "Third Prize", ("third", "三等")),
    (4, "Fourth Prize", ("fourth", "四等")),
    (5, "Fifth Prize", ("fifth", "五等")),
]
CUSTOM_LEVEL_RANK = 99


def normalize_group(name: Optional[str]) -> str:
    """Normalize a department/group name for comparison."""
    if not name:
        return ""
    text = " ".join(str(name).strip().lower().split())
    if text.endswith(" group"):
        text = text[: -len(" group")].strip()
    return text


def level_rank_from_name(name: str) -> int:
    lowered = (name or "").lower()
    for rank, _label, keys in _LEVEL_KEYWORDS:
        for key in keys:
            if key in lowered:
                return rank
    return CUSTOM_LEVEL_RANK


def level_label_from_rank(rank: int) -> str:
    for r, label, _keys in _LEVEL_KEYWORDS:
        if r == rank:
            return label
    return "Custom Prize"


@dataclass
class User:
    """A lottery participant."""

    name: str
    department: str

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.department = str(self.department).strip()

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
    level: Optional[str] = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.quantity = int(self.quantity)
        self.avoid_groups = [str(g).strip() for g in (self.avoid_groups or []) if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer or None
        if not self.level:
            self.level = level_label_from_rank(level_rank_from_name(self.name))

    @property
    def level_rank(self) -> int:
        """Lower value means higher prize level."""
        rank = level_rank_from_name(self.level or "")
        if rank == CUSTOM_LEVEL_RANK:
            rank = level_rank_from_name(self.name)
        return rank

    def __str__(self) -> str:
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "None"
        return (f"{self.name} | Quantity: {self.quantity} | Avoid groups: {avoid} "
                f"| Lottery person: {drawer}")
