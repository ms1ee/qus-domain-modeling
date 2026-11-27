"""Prize library management, avoidance groups and lottery ordering."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Keeps the ordered list of prizes; list order is the lottery sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty.")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        groups = list(dict.fromkeys(groups))
        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = associated_drawer.strip()

        prize = Prize(name=name, quantity=quantity, avoid_groups=groups,
                      associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def update_avoid_groups(self, name: str, avoid_groups: list[str]) -> bool:
        """Replace the avoidance groups of the named prize."""
        groups = [g.strip() for g in avoid_groups if g and g.strip()]
        for prize in self._prizes:
            if prize.name == name:
                prize.avoid_groups = list(dict.fromkeys(groups))
                return True
        return False

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """order: 1-based current positions, listed in the new order."""
        n = len(self._prizes)
        if len(order) != n:
            return False
        if not all(isinstance(i, int) and not isinstance(i, bool) for i in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
