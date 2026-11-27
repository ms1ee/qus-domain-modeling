from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        presets = [
            ("Third Prize - Movie Tickets", 3),
            ("Second Prize - Shopping Cards", 2),
            ("First Prize - 1 Day Annual Leave", 1),
        ]
        for name, q in presets:
            try:
                self.add_prize(name, q)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer")
        p = Prize(name, quantity, list(avoid_groups or []), associated_drawer or None)
        self.prizes.append(p)
        return p

    def get_prizes(self):
        return list(self.prizes)

    def reorder_prizes(self, order):
        n = len(self.prizes)
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
