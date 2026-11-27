"""Core data models for the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(eq=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn during the lottery.

    avoid_groups: list of department groups whose members are excluded.
    associated_drawer: name of the lottery person bound to this prize, or None.
    """

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
