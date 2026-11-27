"""Domain models used across the lottery system."""

from dataclasses import dataclass, field
from typing import Optional

from lottery_system.config import DEFAULT_LEVEL, LEVEL_KEYWORDS


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups whose members are excluded from this prize.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    @property
    def level(self) -> int:
        """Prize level derived from the name; smaller value means higher prize."""
        lowered = self.name.strip().lower()
        for keyword, value in LEVEL_KEYWORDS.items():
            if lowered.startswith(keyword):
                return value
        return DEFAULT_LEVEL
