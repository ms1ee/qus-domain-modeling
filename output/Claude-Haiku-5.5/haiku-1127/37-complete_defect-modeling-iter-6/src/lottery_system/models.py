"""Core data models shared across the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


def normalize_text(value: str) -> str:
    """Normalize text for case-insensitive, whitespace-insensitive comparison."""
    return " ".join(str(value).split()).casefold()


@dataclass(frozen=True)
class User:
    """A participant in the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
