"""Core data models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class User:
    """A participant in the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize with its quantity and lottery rules.

    avoid_groups: department groups whose members are drawn only after
        all other eligible members.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
