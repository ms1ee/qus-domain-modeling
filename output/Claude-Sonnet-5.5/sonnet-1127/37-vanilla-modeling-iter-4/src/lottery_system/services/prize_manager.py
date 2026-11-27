from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        self.add_prize("Third Prize - Movie Tickets", 3, [], "Chen Qixian")
        self.add_prize("Second Prize - Shopping Cards", 2, [], "Jin Duo")
        self.add_prize("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi")
        return []

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        p = Prize(name, quantity, list(avoid_groups or []), associated_drawer)
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
