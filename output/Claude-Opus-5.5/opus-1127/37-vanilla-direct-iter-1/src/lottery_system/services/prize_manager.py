"""Prize configuration management."""

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the prize library and the lottery round order."""

    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        for name, qty, avoid, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, qty, list(avoid), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def _find(self, name):
        for p in self.prizes:
            if p.name == name:
                return p
        return None

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = str(name).strip() if name is not None else ""
        if not name:
            raise ValueError("Prize name must not be empty")
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for prize '{name}': {quantity}")
        if qty <= 0:
            raise ValueError(f"Quantity for prize '{name}' must be a positive integer")
        if self._find(name) is not None:
            raise ValueError(f"Prize '{name}' already exists")
        groups = []
        for g in avoid_groups or []:
            g = str(g).strip()
            if g and g not in groups:
                groups.append(g)
        prize = Prize(name, qty, groups, associated_drawer)
        self.prizes.append(prize)
        return prize

    def set_avoid_groups(self, index, groups):
        if not 0 <= index < len(self.prizes):
            return False
        cleaned = []
        for g in groups or []:
            g = str(g).strip()
            if g and g not in cleaned:
                cleaned.append(g)
        self.prizes[index].avoid_groups = cleaned
        return True

    def get_prizes(self):
        return list(self.prizes)

    def reorder_prizes(self, order):
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        n = len(self.prizes)
        if len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
