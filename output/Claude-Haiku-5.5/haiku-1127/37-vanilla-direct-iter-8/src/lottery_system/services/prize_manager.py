"""Prize library management, avoidance groups and lottery ordering."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize


class PrizeManager:
    """Manages the list of prizes and their lottery order."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            if self._find_index(name) is not None:
                errors.append(f"Prize '{name}' already exists and was skipped.")
                continue
            self._prizes.append(Prize(name, quantity, [], None))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a custom prize at the end of the lottery order."""
        clean_name = " ".join(str(name).split())
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if self._find_index(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        groups = self._clean_groups(avoid_groups)
        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = " ".join(associated_drawer.split())
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in lottery order (the Prize objects are shared)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            positions = [int(value) for value in order]
        except (TypeError, ValueError):
            return False
        count = len(self._prizes)
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True

    def _find_index(self, name: str) -> int | None:
        key = normalize(name)
        for index, prize in enumerate(self._prizes):
            if normalize(prize.name) == key:
                return index
        return None

    @staticmethod
    def _clean_groups(groups: list[str] | None) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for group in groups or []:
            cleaned = " ".join(str(group).split())
            key = normalize(cleaned)
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result
