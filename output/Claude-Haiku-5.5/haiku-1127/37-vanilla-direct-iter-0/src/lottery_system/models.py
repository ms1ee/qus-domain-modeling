"""Domain models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Department group names with special meaning in the rule engine.
CHENG_RU_GROUP = "Cheng Ru group"

# Lottery persons with special meaning in the rule engine.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn during the lottery.

    avoid_groups: department groups excluded from this prize's draw.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
