"""Prize library management."""

from __future__ import annotations

from ..config import DEFAULT_PRIZES
from ..models import Prize


class PrizeManager:
    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = name.strip().casefold()
        for prize in self._prizes:
            if prize.name.strip().casefold() == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages (if any)."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists and was skipped: {name}")
                continue
            self._prizes.append(Prize(name, quantity, [], drawer))
        return errors

    def add_prize(self, name: str, quantity: int,
                  avoid_groups: list[str] | None = None,
                  associated_drawer: str | None = None) -> None:
        name = (name or "").strip()
        if not name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if self._find(name) is not None:
            raise ValueError(f"prize '{name}' already exists")

        groups: list[str] = []
        for group in avoid_groups or []:
            group = (group or "").strip()
            if group and group not in groups:
                groups.append(group)

        drawer = (associated_drawer or "").strip() or None
        self._prizes.append(Prize(name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count or sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
