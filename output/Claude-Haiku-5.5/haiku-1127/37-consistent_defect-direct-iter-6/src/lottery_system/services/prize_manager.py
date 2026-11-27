"""Prize library management, avoidance group configuration and ordering."""

from __future__ import annotations

from collections.abc import Iterable

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize list and the lottery round order."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: Iterable[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a prize to the end of the round order.

        Raises ValueError on invalid input.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if any(p.name == clean_name for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer else ""
        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer or None,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return copies of the prizes in current round order."""
        return [
            Prize(
                name=p.name,
                quantity=p.quantity,
                avoid_groups=list(p.avoid_groups),
                associated_drawer=p.associated_drawer,
            )
            for p in self._prizes
        ]

    def set_avoid_groups(self, name: str, groups: Iterable[str]) -> bool:
        """Replace the avoidance groups of the named prize."""
        prize = self._find(name)
        if prize is None:
            return False
        prize.avoid_groups = [g.strip() for g in groups if g and g.strip()]
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count:
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    def _find(self, name: str) -> Prize | None:
        for prize in self._prizes:
            if prize.name == name:
                return prize
        return None
