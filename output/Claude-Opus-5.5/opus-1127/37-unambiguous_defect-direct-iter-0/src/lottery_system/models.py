"""Core data models for the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


CHENG_RU_GROUP = "Cheng Ru group"
SPECIAL_DRAWER_RELAXED = "Li Bin"
FALLBACK_WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def normalize(text: Optional[str]) -> str:
    """Normalize a string for case/space-insensitive comparisons."""
    if text is None:
        return ""
    return " ".join(str(text).split()).lower()


def is_cheng_ru_group(department: Optional[str]) -> bool:
    """Return True if the department is the Cheng Ru group."""
    norm = normalize(department)
    return norm == normalize(CHENG_RU_GROUP) or norm == "cheng ru"


@dataclass
class User:
    name: str
    department: str

    def __post_init__(self):
        self.name = " ".join(str(self.name).split())
        self.department = " ".join(str(self.department).split())

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if self.associated_drawer is not None:
            drawer = " ".join(str(self.associated_drawer).split())
            self.associated_drawer = drawer or None

    def rule_description(self) -> str:
        parts = []
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: none")
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}")
            if normalize(self.associated_drawer) == normalize(SPECIAL_DRAWER_RELAXED):
                parts.append("Relaxed filtering rules apply (avoidance groups ignored)")
            if normalize(self.associated_drawer) == normalize(FALLBACK_TARGET_DRAWER):
                parts.append(
                    "Cheng Ru group protection may apply if previous two draws "
                    "(Chen Qixian, Jin Duo) had no Cheng Ru group winners"
                )
        else:
            parts.append("Lottery person: not specified")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)


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


def prize_level(prize_name: str) -> int:
    """Return a numeric level for a prize (lower is higher-level)."""
    norm = normalize(prize_name)
    best = None
    for keyword, level in _LEVEL_KEYWORDS:
        if norm.startswith(keyword):
            return level
        if keyword in norm.split() or f"{keyword} prize" in norm:
            if best is None or level < best:
                best = level
    return best if best is not None else 100
