"""Domain models for the team building lottery system."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str]
    associated_drawer: str | None


UNRANKED_LEVEL = 99
_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_LEVEL_PATTERN = re.compile(
    r"\b(first|second|third|fourth|fifth)\s+prize\b", re.IGNORECASE
)


def prize_level_rank(prize_name: str) -> int:
    """Return a numeric rank for a prize level (1 = highest). Unknown levels rank last."""
    match = _LEVEL_PATTERN.search(prize_name or "")
    if match is None:
        return UNRANKED_LEVEL
    return _LEVEL_WORDS[match.group(1).lower()]


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Sort prizes from highest level to lowest, keeping configured order within a level."""
    indexed = list(enumerate(prizes))
    indexed.sort(key=lambda item: (prize_level_rank(item[1].name), item[0]))
    return [prize for _, prize in indexed]
