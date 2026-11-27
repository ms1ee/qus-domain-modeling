"""Prize library management."""

from typing import List

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], None),
    ("Second Prize - Shopping Cards", 3, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]


class PrizeManager:
    """Manages the prize library and lottery round sequence."""

    def __init__(self):
        self.prizes: List[Prize] = []
        self.is_preset = False

    def load_default_prizes(self) -> List[str]:
        errors = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            if not self.add_prize(name, qty, list(avoid), drawer):
                errors.append(f"Failed to add preset prize '{name}'")
        self.is_preset = True
        return errors

    def _find(self, name):
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> bool:
        if not isinstance(name, str) or not name.strip():
            return False
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            return False
        if qty <= 0:
            return False
        if self._find(name.strip()) is not None:
            return False
        self.prizes.append(Prize(name.strip(), qty, list(avoid_groups or []), associated_drawer))
        return True

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def set_avoid_groups(self, index, groups) -> bool:
        if not 0 <= index < len(self.prizes):
            return False
        self.prizes[index].avoid_groups = [g.strip() for g in groups if g and g.strip()]
        return True

    def reorder_prizes(self, order) -> bool:
        n = len(self.prizes)
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
