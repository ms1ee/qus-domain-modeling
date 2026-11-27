"""Core data models for the lottery system."""

from dataclasses import dataclass, field


@dataclass
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups whose members must NOT win this prize.
    associated_drawer: the lottery person linked to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
