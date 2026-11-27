"""Prize configuration management."""

from typing import List, Optional

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Holds the ordered prize library."""

    def __init__(self) -> None:
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None,
                  associated_drawer: Optional[str] = None) -> Prize:
        name = str(name).strip() if name is not None else ""
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if isinstance(quantity, float) and quantity != qty:
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be positive")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists")
        groups: List[str] = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        prize = Prize(name, qty, groups, associated_drawer)
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

    def clear(self) -> None:
        self._prizes = []
