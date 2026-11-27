"""Core data models used across the lottery system."""

from dataclasses import dataclass, field
from typing import Optional


def normalize_text(text: str) -> str:
    """Normalize a name or group for case-insensitive, whitespace-tolerant comparison."""
    return " ".join(str(text).split()).casefold()


@dataclass
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize in the lottery.

    avoid_groups: department groups whose members cannot win this prize.
    associated_drawer: the lottery person bound to this prize (None if not set).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
