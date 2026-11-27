from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Manages prize library and round order."""

    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        existing = {p.name for p in self.prizes}
        for name, qty in DEFAULT_PRIZES:
            if name in existing:
                errors.append(f"Prize '{name}' already exists, skipped.")
                continue
            self.prizes.append(Prize(name, qty, [], None))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty.")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Prize quantity must be a positive integer.")
        if qty <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer: Optional[str] = None
        if associated_drawer is not None and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()
        prize = Prize(str(name).strip(), qty, groups, drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            idx = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idx]
        return True
