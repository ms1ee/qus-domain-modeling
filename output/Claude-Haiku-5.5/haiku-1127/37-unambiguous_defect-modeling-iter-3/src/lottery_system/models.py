"""Domain models for the team building lottery system."""
from __future__ import annotations

from dataclasses import dataclass, field

_LEVEL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}
DEFAULT_LEVEL = 99


def parse_level_from_name(name: str) -> int:
    """Derive a prize level from a leading ordinal word such as 'First Prize'.

    Lower numbers represent higher prize levels. Unknown names get DEFAULT_LEVEL.
    """
    words = name.strip().split()
    if not words:
        return DEFAULT_LEVEL
    return _LEVEL_WORDS.get(words[0].casefold(), DEFAULT_LEVEL)


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round.

    avoid_groups: department groups whose members must not win this prize.
    associated_drawer: the lottery person bound to this prize (or None).
    level: prize level, 1 is the highest; derived from the name when omitted.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int | None = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if self.level is None:
            self.level = parse_level_from_name(self.name)
