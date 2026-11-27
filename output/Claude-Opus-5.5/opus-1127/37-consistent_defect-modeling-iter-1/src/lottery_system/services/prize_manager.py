"""Prize library management."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize, normalize_name

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Holds the ordered list of prizes (lottery round sequence)."""

    def __init__(self) -> None:
        self.prizes: List[Prize] = []
        self.is_preset: bool = False

    def _find(self, name: str) -> Optional[Prize]:
        key = normalize_name(name)
        for prize in self.prizes:
            if normalize_name(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            self.prizes.append(Prize(name, qty, [], None))
        self.is_preset = True
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Prize quantity must be a positive integer")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError("Prize quantity must be a positive integer")
        if qty <= 0:
            raise ValueError("Prize quantity must be a positive integer")
        if self._find(str(name)) is not None:
            raise ValueError(f"Prize '{str(name).strip()}' already exists")
        prize = Prize(str(name), qty, list(avoid_groups or []), associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            indexes = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(indexes) != n or sorted(indexes) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in indexes]
        return True
