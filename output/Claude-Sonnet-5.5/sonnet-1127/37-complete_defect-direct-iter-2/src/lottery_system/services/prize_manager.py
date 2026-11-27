from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        defaults = [
            ("Third Prize - Movie Tickets", 3),
            ("Second Prize - Shopping Cards", 2),
            ("First Prize - 1 Day Annual Leave", 1),
        ]
        for name, q in defaults:
            try:
                self.add_prize(name, q)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer")
        if not name or quantity <= 0:
            raise ValueError("Invalid prize name or quantity")
        self.prizes.append(Prize(name, quantity, list(avoid_groups or []),
                                 associated_drawer or None))

    def get_prizes(self):
        return list(self.prizes)

    def reorder_prizes(self, order):
        n = len(self.prizes)
        if not isinstance(order, (list, tuple)) or len(order) != n:
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
