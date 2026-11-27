"""Prize library management: presets, custom prizes, avoidance groups and ordering."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, avoid, drawer in DEFAULT_PRIZE_SPECS:
            if self._find_index(name) is not None:
                errors.append(f"Prize '{name}' already exists and was skipped")
                continue
            self._prizes.append(Prize(name, quantity, list(avoid), drawer))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find_index(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = (group or "").strip()
            if cleaned and cleaned.casefold() not in {g.casefold() for g in groups}:
                groups.append(cleaned)

        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups: list[str]) -> bool:
        """Replace the avoidance groups of the prize at a 0-based index."""
        if index < 0 or index >= len(self._prizes):
            return False
        cleaned: list[str] = []
        for group in groups:
            value = (group or "").strip()
            if value and value.casefold() not in {g.casefold() for g in cleaned}:
                cleaned.append(value)
        self._prizes[index].avoid_groups = cleaned
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    def _find_index(self, name: str) -> int | None:
        key = name.strip().casefold()
        for index, prize in enumerate(self._prizes):
            if prize.name.strip().casefold() == key:
                return index
        return None
