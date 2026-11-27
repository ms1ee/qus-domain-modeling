"""Prize configuration management."""
from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the prize library and the round order."""

    def __init__(self):
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists")
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

    def get_prize(self, name) -> Optional[Prize]:
        for p in self._prizes:
            if p.name == name:
                return p
        return None

    def remove_prize(self, index: int) -> bool:
        if 1 <= index <= len(self._prizes):
            del self._prizes[index - 1]
            return True
        return False

    def set_avoid_groups(self, name, groups) -> bool:
        prize = self.get_prize(name)
        if prize is None:
            return False
        prize.avoid_groups = [str(g).strip() for g in (groups or []) if str(g).strip()]
        return True

    def reorder_prizes(self, order) -> bool:
        n = len(self._prizes)
        try:
            idx = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in idx]
        return True
