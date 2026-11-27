from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        for name, qty in [
            ("Third Prize - Movie Tickets", 3),
            ("Second Prize - Shopping Cards", 2),
            ("First Prize - 1 Day Annual Leave", 1),
        ]:
            try:
                self.add_prize(name, qty)
            except Exception as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Invalid prize name or quantity")
        p = Prize(name, quantity, list(avoid_groups or []), associated_drawer)
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
