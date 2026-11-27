"""Core data models shared across the lottery system."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """A lottery participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups whose members are excluded from this round.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str]
    associated_drawer: str | None
