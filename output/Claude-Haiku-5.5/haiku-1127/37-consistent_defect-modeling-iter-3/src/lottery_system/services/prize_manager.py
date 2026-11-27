"""Prize library management and prize ordering."""

from __future__ import annotations

import re

from lottery_system.models import UNRANKED_LEVEL, Prize

PRESET_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_LEVEL_PATTERN = re.compile(r"^\s*(First|Second|Third|Fourth|Fifth)\s+Prize", re.IGNORECASE)


def parse_level(name: str) -> int:
    """Derive prize level from its name prefix (e.g. 'First Prize ...' -> 1)."""
    match = _LEVEL_PATTERN.match(name or "")
    if not match:
        return UNRANKED_LEVEL
    return _LEVEL_WORDS[match.group(1).lower()]


class PrizeManager:
    """Manages the prize list and lottery round order. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in PRESET_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a prize to the end of the lottery sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty.")
        if any(p.name.casefold() == name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")

        groups: list[str] = []
        for group in avoid_groups or []:
            group = (group or "").strip()
            if group and group not in groups:
                groups.append(group)

        drawer = (associated_drawer or "").strip() or None

        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
            level=parse_level(name),
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            normalized = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if len(normalized) != count or sorted(normalized) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        return True
