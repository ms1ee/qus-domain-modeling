"""Core domain models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
DRAWER_CHOICES = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)


def normalize(text: str) -> str:
    """Return a canonical form of a name or group for case/space-insensitive comparison."""
    return " ".join((text or "").split()).casefold()


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery configuration.

    avoid_groups: departments whose members may not win this prize.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
