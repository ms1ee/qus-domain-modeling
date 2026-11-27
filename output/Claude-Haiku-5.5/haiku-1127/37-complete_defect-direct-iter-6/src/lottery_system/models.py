"""Core data models and shared helpers for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def normalize_text(value: str) -> str:
    """Normalize a name or group for case-insensitive, whitespace-tolerant comparison."""
    return " ".join(str(value).split()).casefold()


def is_same_group(first: str, second: str) -> bool:
    """Return True when two department/group names refer to the same group."""
    return normalize_text(first) == normalize_text(second)


@dataclass(frozen=True)
class User:
    """A team building participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery configuration."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
