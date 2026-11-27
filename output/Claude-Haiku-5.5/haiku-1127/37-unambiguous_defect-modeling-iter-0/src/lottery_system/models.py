"""Core data models and small shared helpers."""

import re
from dataclasses import dataclass, field

_LEVEL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}

# Prizes without a recognizable level word are placed after all leveled prizes.
UNLEVELED_PRIZE = 99


def normalize_text(text) -> str:
    """Normalize text for case-insensitive, whitespace-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


def prize_level(name: str) -> int:
    """Derive the prize level (1 = highest) from the prize name, e.g. 'First Prize - ...'."""
    for word in re.findall(r"[a-z]+", str(name).casefold()):
        if word in _LEVEL_WORDS:
            return _LEVEL_WORDS[word]
    return UNLEVELED_PRIZE


@dataclass
class User:
    name: str
    department: str


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        return prize_level(self.name)
