"""Prize configuration: prize library, avoidance groups and ordering."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the prizes and their lottery order."""

    def __init__(self) -> None:
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, quantity, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def _find(self, name: str) -> Optional[Prize]:
        for prize in self._prizes:
            if prize.name == name:
                return prize
        return None

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = (name or "").strip() if isinstance(name, str) else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        if isinstance(quantity, bool):
            raise ValueError("Prize quantity must be a positive integer")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Prize quantity must be a positive integer")
        if qty <= 0 or (isinstance(quantity, float) and quantity != qty):
            raise ValueError("Prize quantity must be a positive integer")
        if self._find(name) is not None:
            raise ValueError(f"Prize '{name}' already exists")
        prize = Prize(name, qty, list(avoid_groups or []), associated_drawer)
        self._prizes.append(prize)
        return prize

    def set_avoid_groups(self, index: int, groups) -> bool:
        """Set avoidance groups of the prize at 0-based ``index``."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].avoid_groups = [g.strip() for g in groups if g and g.strip()]
        return True

    def get_prizes(self) -> List[Prize]:
        return list(self._prizes)

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
