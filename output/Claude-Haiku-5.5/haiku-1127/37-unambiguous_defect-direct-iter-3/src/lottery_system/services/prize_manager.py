"""Prize library management and lottery ordering."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZE_SPECS:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"Cannot load preset prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the lottery sequence (addition order)."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name cannot be empty")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        groups = list(dict.fromkeys(avoid_groups or []))
        drawer = associated_drawer.strip() if associated_drawer else None
        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer or None,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. ``order`` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count:
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
