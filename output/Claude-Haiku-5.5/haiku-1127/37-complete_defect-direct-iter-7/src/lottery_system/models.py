"""Domain models for the lottery system."""
from __future__ import annotations

from dataclasses import dataclass, field


def normalize(text: str) -> str:
    """Normalize a name or department for case-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


@dataclass(frozen=True)
class User:
    """A participant in the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
