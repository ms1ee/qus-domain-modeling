"""Prize library management and prize ordering."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the ordered list of prizes. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
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
        """Append a prize to the end of the draw order.

        Raises ValueError when the input is invalid.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(p.name == clean_name for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

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

    def set_avoid_groups(self, name: str, avoid_groups: list[str]) -> bool:
        """Replace the avoidance groups of an existing prize."""
        for prize in self._prizes:
            if prize.name == name:
                prize.avoid_groups = self._clean_groups(avoid_groups)
                return True
        return False

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current draw order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count:
            return False
        if set(order) != set(range(1, count + 1)):
            return False
        if any(not isinstance(pos, int) or isinstance(pos, bool) for pos in order):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in order]
        return True

    @staticmethod
    def _clean_groups(groups: list[str] | None) -> list[str]:
        if not groups:
            return []
        cleaned: list[str] = []
        for group in groups:
            text = (group or "").strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned
