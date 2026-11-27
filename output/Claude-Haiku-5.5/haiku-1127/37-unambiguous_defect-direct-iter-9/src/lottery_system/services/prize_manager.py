"""Prize library management."""
from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of configured prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
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
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a prize at the end of the lottery sequence. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups or []:
            text = str(group).strip()
            if text and text.casefold() not in seen:
                seen.add(text.casefold())
                groups.append(text)

        drawer = (associated_drawer or "").strip() or None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        count = len(self._prizes)
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in positions]
        return True
