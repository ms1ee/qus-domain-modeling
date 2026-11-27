"""Core data models."""
import re
from typing import List, Optional

PROTECTED_GROUP = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
FALLBACK_TRIGGER_PERSONS = ["Chen Qixian", "Jin Duo"]
FALLBACK_TARGET_PERSON = "Ma Jiaqi"


class User:
    """A participant: name plus department group."""

    def __init__(self, name: str, department: str):
        self.name = name.strip()
        self.department = department.strip()

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


class Prize:
    """A prize with quantity, avoidance groups and an optional associated drawer."""

    def __init__(self, name: str, quantity: int, avoid_groups: Optional[List[str]] = None,
                 associated_drawer: Optional[str] = None):
        self.name = name.strip()
        self.quantity = int(quantity)
        self.avoid_groups = list(avoid_groups) if avoid_groups else []
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        self.associated_drawer = drawer or None

    @property
    def level(self) -> int:
        return prize_level(self.name)

    def __repr__(self):
        return (f"Prize(name={self.name!r}, quantity={self.quantity}, "
                f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})")


_LEVEL_WORDS = [
    (("grand", "special", "super"), 0),
    (("first", "1st"), 1),
    (("second", "2nd"), 2),
    (("third", "3rd"), 3),
    (("fourth", "4th"), 4),
    (("fifth", "5th"), 5),
    (("sixth", "6th"), 6),
    (("participation", "consolation", "lucky"), 50),
]

UNKNOWN_LEVEL = 100


def prize_level(name: str) -> int:
    """Return numeric level for a prize name; smaller is higher."""
    lower = name.lower()
    for words, level in _LEVEL_WORDS:
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", lower):
                return level
    return UNKNOWN_LEVEL
