"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
