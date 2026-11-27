"""Prize library management."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        return next((p for p in self._prizes if p.name == name), None)

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists; skipped.")
                continue
            self._prizes.append(Prize(name, quantity, list(avoid_groups), drawer))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a custom prize at the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        groups = list(dict.fromkeys(groups))
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(clean_name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in lottery sequence order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count:
            return False
        if set(order) != set(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
