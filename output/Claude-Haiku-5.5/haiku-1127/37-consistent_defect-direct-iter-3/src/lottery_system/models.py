"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass

# Department group that receives "Cheng Ru group" protection.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons referenced by special rules.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def normalize_text(value: str | None) -> str:
    """Return a case-insensitive, whitespace-trimmed key for comparisons."""
    if value is None:
        return ""
    return value.strip().casefold()


@dataclass(frozen=True)
class User:
    """A participant in the team building lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery sequence.

    avoid_groups: department groups whose members are drawn only after other members.
    associated_drawer: the lottery person responsible for this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str]
    associated_drawer: str | None
