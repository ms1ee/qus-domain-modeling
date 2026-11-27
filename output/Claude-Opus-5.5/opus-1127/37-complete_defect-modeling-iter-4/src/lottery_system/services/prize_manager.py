"""Prize configuration management."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Manages the prize library and lottery sequence."""

    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Prize name must not be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if any(p.name == name.strip() for p in self.prizes):
            raise ValueError(f"Prize '{name.strip()}' already exists")
        groups = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        prize = Prize(name.strip(), qty, groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def get_prize(self, index: int) -> Optional[Prize]:
        if 0 <= index < len(self.prizes):
            return self.prizes[index]
        return None

    def set_avoid_groups(self, index: int, groups: List[str]) -> bool:
        prize = self.get_prize(index)
        if prize is None:
            return False
        prize.avoid_groups = []
        for g in groups:
            g = str(g).strip()
            if g and g not in prize.avoid_groups:
                prize.avoid_groups.append(g)
        return True

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
