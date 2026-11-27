"""Prize library management."""

from __future__ import annotations

from lottery_system.constants import DEFAULT_PRIZE_RECORDS
from lottery_system.models import Prize, normalize_key


class PrizeManager:
    """Manages the ordered list of prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZE_RECORDS:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Prize Error: '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the end of the lottery sequence."""
        prize_name = (name or "").strip()
        if not prize_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(normalize_key(p.name) == normalize_key(prize_name) for p in self._prizes):
            raise ValueError(f"Prize '{prize_name}' already exists.")

        groups: list[str] = []
        seen_groups: set[str] = set()
        for group in avoid_groups or []:
            cleaned = " ".join((group or "").split())
            key = normalize_key(cleaned)
            if cleaned and key not in seen_groups:
                seen_groups.add(key)
                groups.append(cleaned)

        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = associated_drawer.strip()

        self._prizes.append(
            Prize(
                name=prize_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. ``order`` holds 1-based current positions."""
        count = len(self._prizes)
        try:
            if len(order) != count or set(order) != set(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
