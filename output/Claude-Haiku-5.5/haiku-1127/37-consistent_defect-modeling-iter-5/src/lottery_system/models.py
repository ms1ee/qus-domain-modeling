"""Core data models for the lottery system."""
from dataclasses import dataclass, field
from typing import Optional

# Special lottery person names and department names referenced by the rule engine.
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru group"


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""
    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round.

    avoid_groups: department groups whose members are drawn only after other members.
    associated_drawer: the lottery person bound to this prize (or None).
    level: prize level, higher value means higher prize (0 for custom prizes).
    """
    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
    level: int = 0
