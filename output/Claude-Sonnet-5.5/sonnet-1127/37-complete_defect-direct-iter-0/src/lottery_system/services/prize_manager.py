from ..models import Prize

PRESETS = [
    ("Third Prize - Movie Tickets", 3),
    ("Second Prize - Shopping Cards", 2),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        errors = []
        for name, qty in PRESETS:
            try:
                self.add_prize(name, qty)
            except Exception as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        prize = Prize(name, quantity, list(avoid_groups or []), associated_drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self):
        return list(self._prizes)

    def reorder_prizes(self, order):
        n = len(self._prizes)
        try:
            if sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
