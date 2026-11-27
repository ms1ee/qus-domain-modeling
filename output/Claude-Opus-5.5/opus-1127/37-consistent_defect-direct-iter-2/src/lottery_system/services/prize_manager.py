"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the prize library and the lottery round order."""

    def __init__(self) -> None:
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        if name is None or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        name = str(name).strip()
        try:
            qty = int(str(quantity).strip())
        except (TypeError, ValueError):
            raise ValueError(f"Invalid prize quantity: {quantity}")
        if qty <= 0:
            raise ValueError(f"Prize quantity must be a positive integer: {quantity}")
        if any(p.name == name for p in self.prizes):
            raise ValueError(f"Prize already exists: {name}")
        groups: List[str] = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        drawer: Optional[str] = None
        if associated_drawer is not None and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()
        prize = Prize(name, qty, groups, drawer)
        self.prizes.append(prize)
        return prize

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

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
