"""Core data models."""
from dataclasses import dataclass, field
from typing import List, Optional


def normalize_group(name: str) -> str:
    """Normalize a group name for comparison (case/space insensitive)."""
    return "".join(str(name).lower().split())


_LEVEL_KEYWORDS = [
    ("special", 0),
    ("grand", 0),
    ("first", 1),
    ("second", 2),
    ("third", 3),
    ("fourth", 4),
    ("fifth", 5),
]

UNKNOWN_LEVEL = 99


@dataclass
class User:
    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: Optional[List[str]] = field(default=None)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if self.associated_drawer is not None:
            self.associated_drawer = str(self.associated_drawer).strip() or None

    @property
    def level(self) -> int:
        """Smaller number = higher prize level."""
        lower = self.name.lower()
        for kw, lvl in _LEVEL_KEYWORDS:
            if kw in lower:
                return lvl
        return UNKNOWN_LEVEL

    def rule_description(self) -> str:
        parts = []
        if self.associated_drawer:
            parts.append(f"Drawer: {self.associated_drawer}")
        else:
            parts.append("Drawer: (not specified)")
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: none")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)
