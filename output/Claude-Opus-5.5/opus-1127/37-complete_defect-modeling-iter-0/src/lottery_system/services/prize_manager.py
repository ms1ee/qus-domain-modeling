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
    """Manages the prize library and round sequence."""

    def __init__(self):
        self.prizes: List[Prize] = []
        self.is_preset = False

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        self.is_preset = True
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = (name or "").strip() if isinstance(name, str) else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if isinstance(avoid_groups, str):
            avoid_groups = [g.strip() for g in avoid_groups.replace("，", ",").split(",")]
        groups: List[str] = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer: Optional[str] = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        prize = Prize(name, qty, groups, drawer or None)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def set_avoid_groups(self, index: int, groups: List[str]) -> bool:
        if not 0 <= index < len(self.prizes):
            return False
        cleaned: List[str] = []
        for g in groups:
            g = g.strip()
            if g and g not in cleaned:
                cleaned.append(g)
        self.prizes[index].avoid_groups = cleaned
        return True

    def reorder_prizes(self, order: List[int]) -> bool:
        n = len(self.prizes)
        try:
            positions = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[p - 1] for p in positions]
        return True
