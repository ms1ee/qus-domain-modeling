"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A participant in the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for one lottery round.

    avoid_groups: department groups whose members must not win this prize.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
