"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

# Special group and lottery person names defined by the PRD.
CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"


def normalize(text: str | None) -> str:
    """Normalize a name or department for case-insensitive, whitespace-tolerant comparison."""
    if text is None:
        return ""
    return " ".join(str(text).split()).casefold()


@dataclass
class User:
    """A participant in the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
