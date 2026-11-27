"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Lottery persons with special rules
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Group protected by the fallback mechanism
CHENG_RU_GROUP = "Cheng Ru Group"

# Suggested lottery persons shown to the operator
DRAWER_CHOICES = (LI_BIN, CHEN_QIXIAN, JIN_DUO, MA_JIAQI)


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
