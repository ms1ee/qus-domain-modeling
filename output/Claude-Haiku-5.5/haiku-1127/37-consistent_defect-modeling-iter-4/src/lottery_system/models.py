"""Core data models used across the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A team building participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery.

    avoid_groups: department groups whose members are drawn only after others.
    associated_drawer: the lottery person bound to this prize (or None).
    level: prize level, 1 being the highest.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = 0
