"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

CHENG_RU_GROUP = "Cheng Ru Group"
SPECIAL_DRAWER = "Li Bin"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def normalize_name(text: Optional[str]) -> str:
    """Normalize a name for comparison (case/space insensitive)."""
    if text is None:
        return ""
    return re.sub(r"\s+", "", str(text)).lower()


def is_cheng_ru_group(department: Optional[str]) -> bool:
    """Return True if the department refers to the Cheng Ru group."""
    norm = normalize_name(department)
    return norm in ("chengrugroup", "chengru")


@dataclass
class User:
    """A participant of the lottery."""

    name: str
    department: str

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.department = str(self.department).strip()

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


_LEVEL_KEYWORDS = [
    ("grand", 0),
    ("special", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
    ("participation", 50),
    ("consolation", 50),
]


def infer_prize_level(name: str) -> int:
    """Infer a prize level from its name (smaller value = higher prize)."""
    low = (name or "").lower()
    for keyword, level in _LEVEL_KEYWORDS:
        if keyword in low:
            return level
    return 100


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
    level: Optional[int] = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        try:
            self.quantity = int(self.quantity)
        except (TypeError, ValueError):
            self.quantity = 0
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer or None
        if self.level is None:
            self.level = infer_prize_level(self.name)

    def __str__(self) -> str:
        parts = [f"{self.name} x{self.quantity}"]
        if self.avoid_groups:
            parts.append(f"avoid: {', '.join(self.avoid_groups)}")
        if self.associated_drawer:
            parts.append(f"drawer: {self.associated_drawer}")
        return " | ".join(parts)
