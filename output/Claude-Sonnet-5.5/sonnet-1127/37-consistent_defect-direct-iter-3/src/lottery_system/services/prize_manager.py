from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        errors = []
        defaults = [
            ("Third Prize - Movie Tickets", 3, ["Product Department"], "Chen Qixian"),
            ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
            ("First Prize - 1 Day Annual Leave", 1, ["Technology Department"], "Ma Jiaqi"),
        ]
        for n, q, a, d in defaults:
            try:
                self.add_prize(n, q, list(a), d)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be an integer")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        drawer = associated_drawer.strip() if associated_drawer else None
        prize = Prize(name, quantity, list(avoid_groups or []), drawer or None)
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
