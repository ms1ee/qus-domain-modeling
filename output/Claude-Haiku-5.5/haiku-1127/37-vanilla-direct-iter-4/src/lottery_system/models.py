"""Core data models for the lottery system."""

from dataclasses import dataclass, field


def normalize(text: str) -> str:
    """Normalize text for case-insensitive and whitespace-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configuration.

    avoid_groups: department groups whose members must not win this prize.
    associated_drawer: the lottery person associated with this prize, if any.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
