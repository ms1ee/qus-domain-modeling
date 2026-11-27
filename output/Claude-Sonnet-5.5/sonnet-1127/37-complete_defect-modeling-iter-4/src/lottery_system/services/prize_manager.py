from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        for n, q in [("Third Prize - Movie Tickets", 3),
                     ("Second Prize - Shopping Cards", 2),
                     ("First Prize - 1 Day Annual Leave", 1)]:
            try:
                self.add_prize(n, q)
            except Exception as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or int(quantity) <= 0:
            raise ValueError("Invalid prize name or quantity")
        self.prizes.append(Prize(name, int(quantity), list(avoid_groups or []),
                                 associated_drawer or None))

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
