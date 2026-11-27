"""Domain models used across the lottery system."""

from __future__ import annotations

import re

# Level words recognised in prize names; lower number means higher prize level.
_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}

# Level assigned to prizes without a recognised level word (sorted last).
DEFAULT_LEVEL = 999


def infer_prize_level(name: str) -> int:
    """Infer the prize level from a prize name such as 'First Prize - ...'."""
    lowered = name.lower()
    for word, level in _LEVEL_WORDS.items():
        if re.search(r"\b" + word + r"\b", lowered):
            return level
    return DEFAULT_LEVEL


class User:
    """A participant in the team building list."""

    def __init__(self, name: str, department: str) -> None:
        self.name = name
        self.department = department

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, department={self.department!r})"


class Prize:
    """A prize with its lottery rules.

    avoid_groups: list of department names whose members may not win this prize.
    associated_drawer: name of the lottery person handling this prize, or None.
    """

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
        is_custom: bool = False,
        level: int | None = None,
        sequence_number: int = 0,
    ) -> None:
        self.name = name
        self.quantity = quantity
        self.avoid_groups: list[str] = list(avoid_groups) if avoid_groups else []
        self.associated_drawer = associated_drawer
        self.is_custom = is_custom
        self.level = level if level is not None else infer_prize_level(name)
        self.sequence_number = sequence_number

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, "
            f"associated_drawer={self.associated_drawer!r})"
        )
