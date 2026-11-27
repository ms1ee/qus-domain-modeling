"""Prize library management."""

from __future__ import annotations

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
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = str(name).strip() if name is not None else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        if isinstance(avoid_groups, str):
            avoid_groups = [g for g in avoid_groups.split(",")]
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def get_prize(self, name) -> Optional[Prize]:
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def reorder_prizes(self, order) -> bool:
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        n = len(self.prizes)
        if n == 0 or len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
