"""Domain models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_PRIZE_LEVEL = 99


def normalize_key(text) -> str:
    """Normalize a name/department/group for case-insensitive comparison."""
    if text is None:
        return ""
    return " ".join(str(text).split()).casefold()


def infer_prize_level(name: str) -> int:
    """Infer the prize level (1 = highest) from the prize name.

    Custom prizes without a recognised level keyword get a low priority
    (large number) so they are ordered after the preset levels.
    """
    lowered = normalize_key(name)
    if "first" in lowered:
        return 1
    if "second" in lowered:
        return 2
    if "third" in lowered:
        return 3
    return DEFAULT_PRIZE_LEVEL


@dataclass(frozen=True)
class User:
    """A participant with a name and department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = 0

    def __post_init__(self) -> None:
        self.avoid_groups = list(self.avoid_groups or [])
        if self.level <= 0:
            self.level = infer_prize_level(self.name)
