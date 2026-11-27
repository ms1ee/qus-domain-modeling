"""Core data models of the lottery system."""

from __future__ import annotations

from typing import List, Optional


def normalize_group(name: Optional[str]) -> str:
    """Normalize a group/department name for comparisons."""
    if name is None:
        return ""
    return " ".join(str(name).strip().split()).lower()


class User:
    """A participant of the lottery."""

    def __init__(self, name: str, department: str):
        self.name = str(name).strip()
        self.department = str(department).strip()
        self.is_valid = True
        self.has_won = False

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


class Prize:
    """A prize to be drawn in one lottery round."""

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
        level: Optional[int] = None,
    ):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups: List[str] = [
            str(g).strip() for g in (avoid_groups or []) if str(g).strip()
        ]
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else associated_drawer
        self.associated_drawer: Optional[str] = drawer or None
        self.level = level

    def get_level(self) -> int:
        """Return a rank (smaller is higher) derived from explicit level or name."""
        if self.level is not None:
            return int(self.level)
        lowered = self.name.lower()
        for keyword, rank in _LEVEL_KEYWORDS:
            if keyword in lowered:
                return rank
        return 100

    def rule_description(self) -> str:
        parts = []
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}")
        else:
            parts.append("Lottery person: (not specified)")
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: none")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)

    def __repr__(self):
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity}, "
            f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})"
        )
