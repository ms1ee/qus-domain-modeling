"""Prize configuration management."""
from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], None),
    ("Second Prize - Shopping Cards", 2, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]


class PrizeManager:
    def __init__(self):
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        existing = {p.name for p in self._prizes}
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            if name in existing:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            try:
                self.add_prize(name, qty, avoid, drawer)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError("Prize quantity must be a positive integer")
        groups: List[str] = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer: Optional[str] = None
        if associated_drawer is not None and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()
        prize = Prize(str(name).strip(), qty, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

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
