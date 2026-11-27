"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field


def normalize_text(text: str) -> str:
    """Normalize a name or department for case/space-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


@dataclass(frozen=True)
class User:
    """A participant in the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
