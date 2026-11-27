"""Prize configuration: preset library, custom prizes and ordering."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

PRESET_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Maintains the prize library and the lottery round sequence."""

    def __init__(self):
        self.prizes: List[Prize] = []
        self.is_preset = False

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in PRESET_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        self.is_preset = True
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty.")
        name = str(name).strip()
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity of prize '{name}' must be a positive integer.")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(avoid_groups, str):
            avoid_groups = [g for g in avoid_groups.split(",")]
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def remove_prize(self, index: int) -> bool:
        if 1 <= index <= len(self.prizes):
            self.prizes.pop(index - 1)
            return True
        return False

    def reorder_prizes(self, order: List[int]) -> bool:
        try:
            positions = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        n = len(self.prizes)
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in positions]
        return True

    def find_prize(self, name: str) -> Optional[Prize]:
        for p in self.prizes:
            if p.name == name:
                return p
        return None
