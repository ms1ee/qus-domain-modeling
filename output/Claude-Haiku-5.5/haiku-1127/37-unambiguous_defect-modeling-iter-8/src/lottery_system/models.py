"""Core data models for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_ORDINAL_LEVELS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
}

UNRANKED_LEVEL = 99


@dataclass
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department names whose members must not win this prize.
    associated_drawer: name of the lottery person in charge of this prize, or None.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def prize_level(prize: Prize) -> int:
    """Return the ranking level of a prize (1 = highest).

    The level is derived from an ordinal word contained in the prize name
    (e.g. "First Prize - ..." -> 1). Prizes without an ordinal word are
    unranked and receive a large level value so they sort after ranked prizes.
    """
    for token in re.findall(r"[A-Za-z]+", prize.name):
        level = _ORDINAL_LEVELS.get(token.lower())
        if level is not None:
            return level
    return UNRANKED_LEVEL
