"""Prize library management."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

PRESET_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], None),
    ("Second Prize - Shopping Cards", 3, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]


class PrizeManager:
    """Holds prizes in lottery-round order (default: addition order)."""

    def __init__(self) -> None:
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in PRESET_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if any(p.name.lower() == name.lower() for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists")
        groups: List[str] = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer: Optional[str] = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        prize = Prize(name, qty, groups, drawer or None)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order) -> bool:
        try:
            positions = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        n = len(self._prizes)
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in positions]
        return True
