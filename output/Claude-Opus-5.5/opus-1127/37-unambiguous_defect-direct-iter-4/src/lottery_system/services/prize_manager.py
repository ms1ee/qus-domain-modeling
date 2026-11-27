"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None,
                  associated_drawer=None) -> Prize:
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be positive")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        groups = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        prize = Prize(name, qty, groups, drawer or None)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def get_prize(self, name) -> Optional[Prize]:
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def set_avoid_groups(self, prize_name, groups) -> bool:
        prize = self.get_prize(prize_name)
        if prize is None:
            return False
        prize.avoid_groups = []
        for g in groups or []:
            g = str(g).strip()
            if g and g not in prize.avoid_groups:
                prize.avoid_groups.append(g)
        return True

    def reorder_prizes(self, order) -> bool:
        try:
            idx = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        n = len(self.prizes)
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idx]
        return True
