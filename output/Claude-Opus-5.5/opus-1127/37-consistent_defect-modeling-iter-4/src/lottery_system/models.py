"""Core data models for the lottery system."""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A participant of the lottery."""

    name: str
    department: str

    def __post_init__(self):
        self.name = (self.name or "").strip()
        self.department = (self.department or "").strip()

    def __hash__(self):
        return hash((self.name, self.department))

    def __str__(self):
        return f"{self.name} ({self.department})"


_LEVEL_KEYWORDS = [
    (r"\bspecial\b", 0),
    (r"\bgrand\b", 0),
    (r"\bfirst\b", 1),
    (r"\bsecond\b", 2),
    (r"\bthird\b", 3),
    (r"\bfourth\b", 4),
    (r"\bfifth\b", 5),
    (r"\bsixth\b", 6),
]


@dataclass
class Prize:
    """A prize configured for one lottery round."""

    name: str
    quantity: int
    avoid_groups: Optional[List[str]] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        self.name = (self.name or "").strip()
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if isinstance(self.associated_drawer, str):
            self.associated_drawer = self.associated_drawer.strip() or None

    @property
    def level(self) -> int:
        """Numeric level: smaller means higher prize. Unknown levels are lowest."""
        lowered = self.name.lower()
        for pattern, lvl in _LEVEL_KEYWORDS:
            if re.search(pattern, lowered):
                return lvl
        return 99

    def __str__(self):
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "None"
        return (f"{self.name} | Quantity: {self.quantity} | "
                f"Avoidance groups: {avoid} | Lottery person: {drawer}")
