"""Domain models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

UNRANKED_LEVEL = 99


@dataclass(frozen=True)
class User:
    """A participant in the team building lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in one lottery round.

    avoid_groups: department groups whose members are drawn after other members.
    associated_drawer: lottery person associated with this prize (or None).
    level: prize rank; 1 is the highest. Unranked prizes use UNRANKED_LEVEL.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = UNRANKED_LEVEL
