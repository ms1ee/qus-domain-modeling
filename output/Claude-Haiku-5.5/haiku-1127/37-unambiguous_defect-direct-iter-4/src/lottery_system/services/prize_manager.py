"""Prize library management: presets, custom prizes, avoidance groups, ordering."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the list of prizes and their lottery sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
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
    ) -> Prize:
        """Add a prize at the end of the lottery sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(prize.name == name for prize in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = group.strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = associated_drawer.strip() if associated_drawer else ""
        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer or None,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        ``order`` contains 1-based current positions in the new order, e.g.
        [3, 1, 2] means the prize at position 3 becomes first.
        Returns False if the order is not a valid permutation.
        """
        count = len(self._prizes)
        if len(order) != count:
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
