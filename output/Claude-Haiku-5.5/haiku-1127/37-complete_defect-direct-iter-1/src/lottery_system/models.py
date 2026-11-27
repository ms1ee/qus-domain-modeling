"""Core data models and shared constants for the lottery system."""

from dataclasses import dataclass

# Department group protected by the fallback rule.
CHENG_RU_GROUP = "Cheng Ru Group"

# Named lottery persons with special rules.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# Lottery persons whose draw results feed the Cheng Ru group fallback history.
FALLBACK_TRIGGER_DRAWERS = (CHEN_QIXIAN, JIN_DUO)


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configuration for one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str]
    associated_drawer: str | None
