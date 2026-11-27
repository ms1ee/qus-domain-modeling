"""Prize library management and ordering."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Failed to add default prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name,
        quantity,
        avoid_groups=None,
        associated_drawer=None,
    ) -> Prize:
        """Append a prize to the lottery sequence.

        Raises ValueError on invalid name, quantity, or duplicate name.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Prize name must not be empty.")
        name = name.strip()
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")

        if isinstance(quantity, bool):
            raise ValueError("Quantity must be a positive integer.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be a positive integer.") from None
        if quantity < 1:
            raise ValueError("Quantity must be a positive integer.")

        groups: list[str] = []
        for group in avoid_groups or []:
            group = str(group).strip()
            if group and group not in groups:
                groups.append(group)

        drawer = None
        if associated_drawer is not None:
            drawer = str(associated_drawer).strip() or None

        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order (a copy of the list)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        order: 1-based current positions, listed in the new order.
        Returns False if order is not a permutation of 1..n.
        """
        n = len(self._prizes)
        try:
            indexes = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if len(indexes) != n or sorted(indexes) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in indexes]
        return True
