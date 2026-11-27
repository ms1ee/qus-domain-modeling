"""Prize library management: presets, custom prizes, rules and ordering."""

from __future__ import annotations

from lottery_system.config import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, [], drawer, is_custom=False)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
        is_custom: bool = True,
    ) -> Prize:
        """Append a prize to the end of the lottery sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(prize.name == name for prize in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        groups = list(dict.fromkeys(groups))
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        prize = Prize(
            name,
            quantity,
            groups,
            drawer,
            is_custom=is_custom,
            sequence_number=len(self._prizes) + 1,
        )
        self._prizes.append(prize)
        return prize

    def update_rules(
        self,
        name: str,
        avoid_groups: list[str] | None,
        associated_drawer: str | None,
    ) -> bool:
        """Update avoidance groups and lottery person of an existing prize."""
        for prize in self._prizes:
            if prize.name == name:
                prize.avoid_groups = list(dict.fromkeys(avoid_groups or []))
                drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
                prize.associated_drawer = drawer
                return True
        return False

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        order holds 1-based current positions in the new order, e.g. [2, 1, 3]
        means the prize at position 2 becomes first. Must be a permutation of
        all current positions; otherwise returns False and changes nothing.
        """
        count = len(self._prizes)
        try:
            positions = [int(value) for value in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, count + 1)):
            return False

        self._prizes = [self._prizes[position - 1] for position in positions]
        for index, prize in enumerate(self._prizes, start=1):
            prize.sequence_number = index
        return True
