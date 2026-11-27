"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A participant with a name and department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configuration.

    avoid_groups: department groups excluded from this prize's draw.
    associated_drawer: the lottery person assigned to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
