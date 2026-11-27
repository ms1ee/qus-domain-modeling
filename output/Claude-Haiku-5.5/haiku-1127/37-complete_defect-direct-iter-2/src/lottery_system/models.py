"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Lottery person names used by the rule engine.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# The group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons that can be associated with a prize, in display order.
LOTTERY_DRAWERS = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)


@dataclass
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
