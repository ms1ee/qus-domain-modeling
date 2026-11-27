"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Holds the ordered prize list (the lottery round sequence)."""

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
        name = (name or "").strip() if isinstance(name, str) else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity of prize '{name}' must be a positive integer")
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

    def get_prize(self, name) -> Optional[Prize]:
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            idx = [int(i) for i in order]
        except (TypeError, ValueError):
            return False
        if len(idx) != n or sorted(idx) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in idx]
        return True
