"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages prizes and their draw order."""

    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        existing = {p.name for p in self.prizes}
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            if name in existing:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Prize quantity must be an integer")
        if qty <= 0:
            raise ValueError("Prize quantity must be positive")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        if drawer == "":
            drawer = None
        prize = Prize(name.strip(), qty, groups, drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            idx = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idx]
        return True
