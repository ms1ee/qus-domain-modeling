"""Domain models shared by all lottery system services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def normalize_group(value: str) -> str:
    """Normalize a name or department for case/whitespace-insensitive comparison."""
    return " ".join(str(value).split()).casefold()


def same_text(a: Optional[str], b: Optional[str]) -> bool:
    """Return True when two optional strings match after normalization."""
    if a is None or b is None:
        return False
    return normalize_group(a) == normalize_group(b)


def is_cheng_ru_group(department: str) -> bool:
    """Return True if the department is the Cheng Ru group."""
    return same_text(department, CHENG_RU_GROUP)


@dataclass(frozen=True)
class User:
    """A lottery participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery configuration.

    avoid_groups: departments that may NOT win this prize.
    associated_drawer: the lottery person associated with this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
