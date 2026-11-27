"""Prize library management."""

from __future__ import annotations

from lottery_system.config import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the ordered list of prizes. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
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
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if self._find_index(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")

        groups = self._clean_groups(avoid_groups)
        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order (a copy of the list)."""
        return list(self._prizes)

    def get_prize(self, name: str) -> Prize | None:
        index = self._find_index(name)
        return None if index is None else self._prizes[index]

    def set_avoid_groups(self, name: str, groups: list[str] | None) -> bool:
        """Replace the avoidance groups of a prize."""
        prize = self.get_prize(name)
        if prize is None:
            return False
        prize.avoid_groups = self._clean_groups(groups)
        return True

    def set_associated_drawer(self, name: str, drawer: str | None) -> bool:
        """Set or clear the associated lottery person of a prize."""
        prize = self.get_prize(name)
        if prize is None:
            return False
        prize.associated_drawer = (drawer or "").strip() or None
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        if not isinstance(order, list):
            return False
        n = len(self._prizes)
        if not all(isinstance(item, int) and not isinstance(item, bool) for item in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    def _find_index(self, name: str) -> int | None:
        target = (name or "").strip().casefold()
        for index, prize in enumerate(self._prizes):
            if prize.name.casefold() == target:
                return index
        return None

    @staticmethod
    def _clean_groups(groups: list[str] | None) -> list[str]:
        cleaned: list[str] = []
        for group in groups or []:
            value = (group or "").strip()
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned
