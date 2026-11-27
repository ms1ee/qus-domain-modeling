"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Lottery persons with special rules
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LOTTERY_PERSONS = (LI_BIN, CHEN_QIXIAN, JIN_DUO, MA_JIAQI)

# Department group protected by the fallback mechanism
CHENG_RU_GROUP = "Cheng Ru Group"


def is_cheng_ru_department(department: str) -> bool:
    """Return True if the department belongs to the Cheng Ru group."""
    return department.strip().casefold() == CHENG_RU_GROUP.casefold()


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in one lottery round.

    avoid_groups: department names whose members are drawn after other members.
    associated_drawer: the lottery person bound to this prize, or None.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
