"""Core data models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


def normalize_text(value: object) -> str:
    """Collapse whitespace and strip surrounding spaces."""
    return " ".join(str(value).split())


def normalize_key(value: object) -> str:
    """Normalized, case-insensitive key used for comparisons."""
    return normalize_text(value).casefold()


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
