"""Prize configuration management."""
from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty in DEFAULT_PRIZES:
            if any(p.name == name for p in self.prizes):
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            self.prizes.append(Prize(name, qty))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = str(name).strip() if name is not None else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Prize quantity must be an integer")
        if qty <= 0:
            raise ValueError("Prize quantity must be positive")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        groups = [str(g).strip() for g in (avoid_groups or []) if str(g).strip()]
        prize = Prize(name, qty, groups, associated_drawer)
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

    def set_avoid_groups(self, index: int, groups) -> bool:
        if not 0 <= index < len(self.prizes):
            return False
        self.prizes[index].avoid_groups = [str(g).strip() for g in groups if str(g).strip()]
        return True

    def set_drawer(self, index: int, drawer: Optional[str]) -> bool:
        if not 0 <= index < len(self.prizes):
            return False
        self.prizes[index].associated_drawer = (drawer or "").strip() or None
        return True
