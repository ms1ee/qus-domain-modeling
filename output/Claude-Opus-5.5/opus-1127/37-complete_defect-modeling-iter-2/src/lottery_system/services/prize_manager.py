"""Prize library management."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, ["Cheng Ru group"], "Ma Jiaqi"),
    ("Special Prize - Lucky Red Envelope", 1, ["Technology Department"], "Li Bin"),
]


class PrizeManager:
    """Manages prizes and their drawing order."""

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
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        name = str(name).strip()
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        groups = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        prize = Prize(name, qty, groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def get_prize(self, name: str) -> Optional[Prize]:
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def set_avoid_groups(self, index: int, groups: List[str]) -> bool:
        if index < 0 or index >= len(self.prizes):
            return False
        cleaned = []
        for g in groups:
            g = str(g).strip()
            if g and g not in cleaned:
                cleaned.append(g)
        self.prizes[index].avoid_groups = cleaned
        return True

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
