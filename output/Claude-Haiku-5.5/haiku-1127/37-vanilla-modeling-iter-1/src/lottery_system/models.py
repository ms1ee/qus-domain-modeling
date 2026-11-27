"""Domain models and shared constants for the lottery system."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Department whose members are protected by the fallback rule.
CHENG_RU_GROUP = "Cheng Ru Group"

# Special lottery person: only previous winners are filtered.
SPECIAL_DRAWER_LI_BIN = "Li Bin"

# Fallback rule: if the last two draws by these persons contained no
# Cheng Ru Group member, the next draw by FALLBACK_TARGET_DRAWER is restricted.
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"

UNRANKED_LEVEL = 9999

_ORDINAL_VALUES = {
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
_ORDINAL_RE = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def prize_level(name: str) -> int:
    """Return the rank of a prize from its name (First=1, Second=2, ...).

    Prizes without an ordinal word are ranked last.
    """
    match = _ORDINAL_RE.search(name or "")
    if match is None:
        return UNRANKED_LEVEL
    return _ORDINAL_VALUES[match.group(1).lower()]


def sort_prizes_by_level(prizes: list[Prize]) -> list[Prize]:
    """Return prizes ordered from highest level to lowest.

    The sort is stable, so prizes of equal level keep their input order.
    """
    return sorted(prizes, key=lambda prize: prize_level(prize.name))
