"""Prize library management: presets, custom prizes, avoidance groups and ordering."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize_key, normalize_text


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize_key(name)
        for prize in self._prizes:
            if normalize_key(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Load preset prizes. Returns a list of error messages (empty on success)."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists, skipped: {name}")
                continue
            self._prizes.append(Prize(name, quantity, [], drawer))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a custom prize at the end of the lottery sequence."""
        clean_name = normalize_text(name)
        if not clean_name:
            raise ValueError("Prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize already exists: {clean_name}")

        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups or []:
            clean_group = normalize_text(group)
            key = normalize_key(clean_group)
            if clean_group and key not in seen:
                seen.add(key)
                groups.append(clean_group)

        drawer = normalize_text(associated_drawer) if associated_drawer else ""
        prize = Prize(clean_name, quantity, groups, drawer or None)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in lottery order (the Prize objects are shared, not copied)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        n = len(self._prizes)
        try:
            if sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
