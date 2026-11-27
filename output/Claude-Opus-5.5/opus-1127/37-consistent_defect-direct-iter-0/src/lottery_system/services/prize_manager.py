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
    """Holds the prize list in lottery order."""

    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        existing = {p.name for p in self.prizes}
        for name, qty in DEFAULT_PRIZES:
            if name in existing:
                errors.append(f"Prize already exists: {name}")
                continue
            try:
                self.add_prize(name, qty)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name,
        quantity,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
    ) -> Prize:
        name = str(name).strip() if name is not None else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError(f"Prize quantity must be positive: {quantity}")
        groups = [str(g).strip() for g in (avoid_groups or []) if str(g).strip()]
        # remove duplicate groups while preserving order
        groups = list(dict.fromkeys(groups))
        prize = Prize(name, qty, groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def set_avoid_groups(self, index: int, groups: List[str]) -> bool:
        """Set avoidance groups for the prize at 0-based index."""
        if not 0 <= index < len(self.prizes):
            return False
        cleaned = [str(g).strip() for g in groups if str(g).strip()]
        self.prizes[index].avoid_groups = list(dict.fromkeys(cleaned))
        return True

    def reorder_prizes(self, order: List[int]) -> bool:
        n = len(self.prizes)
        try:
            idx = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idx]
        return True
