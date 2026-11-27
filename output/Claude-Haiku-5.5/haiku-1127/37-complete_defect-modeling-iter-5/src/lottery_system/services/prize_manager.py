"""Prize library management and round ordering."""

from __future__ import annotations

from typing import Optional

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for a lottery session."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages (empty on success)."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[list[str]] = None,
        associated_drawer: Optional[str] = None,
    ) -> Prize:
        """Add a prize at the end of the current sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order.

        Returns True on success; False if `order` is not a permutation of 1..n.
        """
        n = len(self._prizes)
        if len(order) != n:
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
