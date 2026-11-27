"""Domain models and shared constants for the team building lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def normalize(text: str | None) -> str:
    """Return a whitespace-collapsed, case-insensitive comparison key."""
    if not text:
        return ""
    return " ".join(str(text).split()).casefold()


@dataclass
class User:
    """A participant of the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
