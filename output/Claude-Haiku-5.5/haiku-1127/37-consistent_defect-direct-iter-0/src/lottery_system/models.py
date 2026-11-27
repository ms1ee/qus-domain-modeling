"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Special lottery persons referenced by the lottery rule engine.
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons offered as choices when configuring a prize.
DRAWER_CHOICES = (LI_BIN, CHEN_QIXIAN, JIN_DUO, MA_JIAQI)

_ORDINAL_WORDS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
)


def normalize(text: str | None) -> str:
    """Return a comparison key: whitespace collapsed, case-insensitive."""
    return " ".join((text or "").split()).casefold()


def same_text(first: str | None, second: str | None) -> bool:
    """Case-insensitive, whitespace-tolerant equality check."""
    return normalize(first) == normalize(second)


@dataclass(frozen=True)
class User:
    """A participant in the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def prize_level_rank(name: str | None) -> int:
    """Return the level rank of a prize from its name (1 = highest).

    Names containing an ordinal word such as "First", "Second" or "Third"
    are ranked by that ordinal. Other names rank after all ordinal prizes.
    """
    lowered = (name or "").lower()
    for rank, word in enumerate(_ORDINAL_WORDS, start=1):
        if re.search(r"\b" + word + r"\b", lowered):
            return rank
    return len(_ORDINAL_WORDS) + 1
