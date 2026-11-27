"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Special lottery persons and group rules
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
PROTECTION_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
CHENG_RU_GROUP = "Cheng Ru Group"


@dataclass
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def is_cheng_ru(user: User) -> bool:
    """Return True if the user belongs to the Cheng Ru group."""
    return user.department.strip().lower() == CHENG_RU_GROUP.lower()
