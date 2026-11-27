"""Prize library management."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Keeps the ordered list of configured prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages (if any)."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> None:
        """Add a prize at the end of the current sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = associated_drawer.strip()

        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        if not isinstance(order, (list, tuple)):
            return False
        count = len(self._prizes)
        try:
            if sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
