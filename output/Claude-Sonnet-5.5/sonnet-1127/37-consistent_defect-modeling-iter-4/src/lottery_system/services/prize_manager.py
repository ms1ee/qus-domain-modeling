from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        for name, qty in [("Third Prize - Movie Tickets", 3),
                          ("Second Prize - Shopping Cards", 2),
                          ("First Prize - 1 Day Annual Leave", 1)]:
            self.prizes.append(Prize(name, qty, [], None))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        self.prizes.append(Prize(name, quantity, list(avoid_groups or []), associated_drawer))

    def get_prizes(self):
        return self.prizes

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
