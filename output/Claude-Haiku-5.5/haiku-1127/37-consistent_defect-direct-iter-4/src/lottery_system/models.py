"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field


def normalize_key(text: str) -> str:
    """Return a case-insensitive, whitespace-normalized comparison key."""
    return " ".join((text or "").split()).casefold()


@dataclass(frozen=True)
class User:
    """A lottery participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
