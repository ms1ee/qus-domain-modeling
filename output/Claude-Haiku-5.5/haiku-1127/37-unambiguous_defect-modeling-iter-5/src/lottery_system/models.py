"""Domain models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

from lottery_system.constants import LEVEL_CUSTOM


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = LEVEL_CUSTOM
    sequence_number: int = 0
    is_preset: bool = False
