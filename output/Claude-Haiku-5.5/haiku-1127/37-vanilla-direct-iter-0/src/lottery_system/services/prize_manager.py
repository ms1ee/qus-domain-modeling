"""Prize library management and lottery round ordering."""

from __future__ import annotations

from typing import Iterable

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize list in lottery round order (addition order by default)."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, None, drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: Iterable[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize at the end of the round order. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = associated_drawer.strip() if associated_drawer else None
        drawer = drawer or None

        prize = Prize(clean_name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True
