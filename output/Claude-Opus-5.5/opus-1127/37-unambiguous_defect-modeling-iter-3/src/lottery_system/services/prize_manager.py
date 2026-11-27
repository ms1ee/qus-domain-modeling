"""Prize library management."""
from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    # name, quantity, avoid groups, drawer, level
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian", 3),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo", 2),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi", 1),
]


class PrizeManager:
    """Holds the ordered list of prizes (lottery round sequence)."""

    def __init__(self) -> None:
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer, level in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer, level=level)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None,
                  level: Optional[int] = None) -> Prize:
        name = (name or "").strip() if isinstance(name, str) else name
        if not name or not isinstance(name, str):
            raise ValueError("Prize name cannot be empty")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists")
        try:
            if isinstance(quantity, bool):
                raise ValueError
            qty = int(quantity)
            if isinstance(quantity, float) and quantity != qty:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError(f"Prize quantity must be positive: {quantity}")
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer, level)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order) -> bool:
        n = len(self._prizes)
        try:
            idx = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in idx]
        return True
