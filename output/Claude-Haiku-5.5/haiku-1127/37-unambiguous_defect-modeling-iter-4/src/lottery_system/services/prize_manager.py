"""Prize library management, avoidance groups and ordering."""

from __future__ import annotations

import re

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, ["Technology Department"], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 3, ["Product Department"], "Li Bin"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Ma Jiaqi"),
]

_LEVEL_KEYWORDS = {"first": 3, "second": 2, "third": 1}


def infer_level(name: str) -> int:
    """Infer prize level from its name: First=3, Second=2, Third=1, otherwise 0."""
    match = re.search(r"\b(first|second|third)\b", name.lower())
    if match is None:
        return 0
    return _LEVEL_KEYWORDS[match.group(1)]


class PrizeManager:
    """Manages the ordered list of prizes for a lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns error messages, if any."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a new prize. Raises ValueError on invalid input."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(name=name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        prize.level = infer_level(name)
        self._prizes.append(prize)

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        try:
            normalized = [int(value) for value in order]
        except (TypeError, ValueError):
            return False
        if sorted(normalized) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        return True

    def update_avoid_groups(self, position: int, groups: list[str]) -> bool:
        """Set avoidance groups for the prize at 1-based position."""
        if not 1 <= position <= len(self._prizes):
            return False
        cleaned = [g.strip() for g in groups if g and g.strip()]
        self._prizes[position - 1].avoid_groups = cleaned
        return True

    def remove_prize(self, position: int) -> bool:
        """Remove the prize at 1-based position."""
        if not 1 <= position <= len(self._prizes):
            return False
        del self._prizes[position - 1]
        return True
