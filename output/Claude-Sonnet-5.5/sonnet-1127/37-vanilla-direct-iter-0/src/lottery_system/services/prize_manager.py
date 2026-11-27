from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        errors = []
        for name, q in [("Third Prize - Movie Tickets", 3),
                        ("Second Prize - Shopping Cards", 2),
                        ("First Prize - 1 Day Annual Leave", 1)]:
            try:
                self.add_prize(name, q)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        p = Prize(name, quantity, list(avoid_groups or []), associated_drawer or None)
        self._prizes.append(p)
        return p

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
