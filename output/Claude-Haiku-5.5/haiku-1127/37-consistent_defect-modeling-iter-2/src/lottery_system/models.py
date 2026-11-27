"""Domain models for the team building lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A participant of the lottery, identified by name and department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups whose members are drawn only after
                  all other eligible members.
    associated_drawer: the lottery person bound to this prize (or None).
    level: prize rank used for result ordering (smaller value = higher prize).
    sequence_number: 1-based position in the lottery sequence.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = field(default=0, init=False)
    sequence_number: int = field(default=0, init=False)
