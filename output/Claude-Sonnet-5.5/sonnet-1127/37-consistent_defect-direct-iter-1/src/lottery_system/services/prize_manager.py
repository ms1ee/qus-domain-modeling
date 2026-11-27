from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        errors = []
        defaults = [
            ("Third Prize - Movie Tickets", 3, "Chen Qixian"),
            ("Second Prize - Shopping Cards", 2, "Jin Duo"),
            ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
        ]
        for n, q, d in defaults:
            try:
                self.add_prize(n, q, None, d)
            except Exception as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or int(quantity) <= 0:
            raise ValueError("Invalid prize")
        p = Prize(name, int(quantity), list(avoid_groups or []), associated_drawer)
        self._prizes.append(p)
        return p

    def get_prizes(self):
        return list(self._prizes)

    def reorder_prizes(self, order):
        n = len(self._prizes)
        if len(order) != n or sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
