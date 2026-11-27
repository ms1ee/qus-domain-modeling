"""Prize library management."""

from __future__ import annotations

from ..defaults import DEFAULT_PRIZES
from ..models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"Prize Error for '{name}': {exc}")
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
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        if any(p.name.casefold() == name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = (group or "").strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(name=name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """order holds 1-based current positions in the desired new sequence."""
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if not all(isinstance(i, int) and not isinstance(i, bool) for i in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
