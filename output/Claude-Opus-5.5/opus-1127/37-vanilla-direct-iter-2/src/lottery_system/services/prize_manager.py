"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the prize library and draw order."""

    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            if any(p.name == name for p in self.prizes):
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
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
        prize = Prize(str(name).strip(), qty, avoid_groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def get_prize(self, index: int) -> Optional[Prize]:
        if 0 <= index < len(self.prizes):
            return self.prizes[index]
        return None

    def set_avoid_groups(self, index: int, groups) -> bool:
        prize = self.get_prize(index)
        if prize is None:
            return False
        prize.avoid_groups = [str(g).strip() for g in (groups or []) if str(g).strip()]
        return True

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
