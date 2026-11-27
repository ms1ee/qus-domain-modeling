"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field

CUSTOM_PRIZE_LEVEL = 999
_LEVEL_KEYWORDS = (("first", 1), ("second", 2), ("third", 3))


@dataclass(frozen=True)
class User:
    """A participant with name and department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round.

    avoid_groups: department groups whose members are drawn only after other members.
    associated_drawer: the lottery person bound to this prize (or None).
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int:
        """Prize level derived from the name prefix (First=1, Second=2, Third=3).

        Custom prizes get a lower priority level (larger number)."""
        lowered = self.name.strip().lower()
        for keyword, value in _LEVEL_KEYWORDS:
            if lowered.startswith(keyword):
                return value
        return CUSTOM_PRIZE_LEVEL
