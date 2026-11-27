"""Core data models for the lottery system."""

from dataclasses import dataclass


def normalize(text: str) -> str:
    """Normalize a name or group label for case-insensitive comparison."""
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
    avoid_groups: list[str]
    associated_drawer: str | None
