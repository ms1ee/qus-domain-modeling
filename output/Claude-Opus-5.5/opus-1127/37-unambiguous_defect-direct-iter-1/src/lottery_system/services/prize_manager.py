"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    def __init__(self):
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        existing = {p.name for p in self._prizes}
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            if name in existing:
                errors.append(f"Prize already exists: {name}")
                continue
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None,
                  associated_drawer: Optional[str] = None) -> Prize:
        name = (name or "").strip() if isinstance(name, str) else name
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError("Prize quantity must be a positive integer")
        groups = []
        for g in (avoid_groups or []):
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        prize = Prize(name, qty, groups, associated_drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups) -> bool:
        if not 0 <= index < len(self._prizes):
            return False
        cleaned = []
        for g in groups or []:
            g = str(g).strip()
            if g and g not in cleaned:
                cleaned.append(g)
        self._prizes[index].avoid_groups = cleaned
        return True

    def reorder_prizes(self, order) -> bool:
        n = len(self._prizes)
        try:
            positions = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[p - 1] for p in positions]
        return True
