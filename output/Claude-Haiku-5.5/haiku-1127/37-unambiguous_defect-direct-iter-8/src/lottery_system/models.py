"""Core data models and shared constants for the lottery system."""

from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"


@dataclass
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
