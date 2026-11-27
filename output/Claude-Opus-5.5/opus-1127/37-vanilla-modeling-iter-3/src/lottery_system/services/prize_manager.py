"""Prize configuration management."""

from typing import List

from lottery_system.models import Prize

PRESET_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], None),
    ("Second Prize - Shopping Cards", 2, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]


class PrizeManager:
    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors = []
        for name, qty, avoid, drawer in PRESET_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity of prize '{name}' must be positive")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def reorder_prizes(self, order) -> bool:
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        n = len(self.prizes)
        if len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
