from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        presets = [
            ("Third Prize - Movie Tickets", 3, [], None),
            ("Second Prize - Shopping Cards", 2, [], None),
            ("First Prize - 1 Day Annual Leave", 1, [], None),
        ]
        for name, q, av, dr in presets:
            try:
                self.add_prize(name, q, av, dr)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        p = Prize(name.strip(), quantity, avoid_groups or [], associated_drawer)
        self.prizes.append(p)
        return p

    def get_prizes(self):
        return list(self.prizes)

    def reorder_prizes(self, order):
        n = len(self.prizes)
        try:
            ok = len(order) == n and sorted(order) == list(range(1, n + 1))
        except TypeError:
            return False
        if not ok:
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
