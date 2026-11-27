"""Domain models and shared constants for the lottery system."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru group"

LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

LOTTERY_PERSONS = [LI_BIN, CHEN_QIXIAN, JIN_DUO, MA_JIAQI]

UNRANKED_LEVEL = 99

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

_LEVEL_PATTERN = re.compile(
    r"^\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+prize\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups that must not win this prize.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        """Prize level derived from the name prefix (1 = highest).

        Names such as "First Prize - ..." yield 1, "Second Prize - ..." yield 2, etc.
        Prizes without a recognisable level get the lowest rank.
        """
        match = _LEVEL_PATTERN.match(self.name)
        if match:
            return _LEVEL_WORDS[match.group(1).lower()]
        return UNRANKED_LEVEL
