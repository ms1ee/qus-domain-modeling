"""Domain models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    """A participant in the lottery (name and department group)."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round.

    level is derived from the prize name (First=3, Second=2, Third=1, other=0)
    and is used for ordering results from high to low.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = field(default=0, init=False)
