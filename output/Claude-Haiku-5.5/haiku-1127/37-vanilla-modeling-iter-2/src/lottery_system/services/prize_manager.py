"""Prize library management."""

from lottery_system.data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize library and lottery round order. Starts empty."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        existing = {p.name.casefold() for p in self._prizes}
        for name, quantity, drawer in DEFAULT_PRIZES:
            if name.casefold() in existing:
                continue
            try:
                self.add_prize(name, quantity, [], drawer)
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
        name = (name or "").strip()
        if not name:
            raise ValueError("prize name must not be empty")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = group.strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)
        drawer = associated_drawer.strip() if associated_drawer else None
        if drawer == "":
            drawer = None
        prize = Prize(name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """order[k] is the 1-based current position of the prize that should
        occupy new position k+1."""
        n = len(self._prizes)
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in order]
        return True
