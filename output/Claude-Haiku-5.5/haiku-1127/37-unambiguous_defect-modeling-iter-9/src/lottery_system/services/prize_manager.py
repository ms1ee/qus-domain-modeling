"""Prize library management."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes (draw sequence)."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Replace current prizes with the preset prize library. Returns error messages."""
        self._prizes = []
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a prize to the end of the draw sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if any(p.name == clean_name for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        try:
            qty = int(quantity)
        except (TypeError, ValueError) as exc:
            raise ValueError("Quantity must be an integer.") from exc
        if qty < 1:
            raise ValueError("Quantity must be at least 1.")

        groups = self._normalize_groups(avoid_groups)
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        drawer = drawer or None

        prize = Prize(name=clean_name, quantity=qty, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def set_avoid_groups(self, name: str, avoid_groups: list[str] | None) -> None:
        """Replace the avoidance groups of an existing prize."""
        for prize in self._prizes:
            if prize.name == name:
                prize.avoid_groups = self._normalize_groups(avoid_groups)
                return
        raise ValueError(f"Prize '{name}' not found.")

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current draw order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        n = len(self._prizes)
        if n == 0:
            return False
        try:
            indices = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if sorted(indices) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in indices]
        return True

    @staticmethod
    def _normalize_groups(groups: list[str] | None) -> list[str]:
        result: list[str] = []
        if not groups:
            return result
        for group in groups:
            if not isinstance(group, str):
                continue
            cleaned = group.strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result
