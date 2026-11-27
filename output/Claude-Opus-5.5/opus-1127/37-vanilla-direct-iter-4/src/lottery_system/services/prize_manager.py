"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Manages the prize library and the draw order."""

    def __init__(self) -> None:
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = (name or "").strip() if isinstance(name, str) else name
        if not name:
            raise ValueError("Prize name must not be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError(f"Prize quantity must be positive: {quantity}")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize already exists: {name}")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        prize = Prize(name, qty, groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def set_avoid_groups(self, index: int, groups) -> bool:
        """Set avoidance groups for prize at 1-based index."""
        if not 1 <= index <= len(self.prizes):
            return False
        self.prizes[index - 1].avoid_groups = [g for g in groups if g]
        return True

    def remove_prize(self, index: int) -> Optional[Prize]:
        if not 1 <= index <= len(self.prizes):
            return None
        return self.prizes.pop(index - 1)

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            idxs = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        if len(idxs) != n or sorted(idxs) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idxs]
        return True
