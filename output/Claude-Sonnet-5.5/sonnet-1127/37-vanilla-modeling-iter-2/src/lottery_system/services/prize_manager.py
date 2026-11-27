from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes = []

    def load_default_prizes(self):
        errors = []
        presets = [
            ("Third Prize - Movie Tickets", 3, "Chen Qixian"),
            ("Second Prize - Shopping Cards", 2, "Jin Duo"),
            ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
        ]
        for name, q, d in presets:
            try:
                self.add_prize(name, q, [], d)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or not str(name).strip():
            raise ValueError("Prize name cannot be empty")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        self.prizes.append(Prize(name, quantity, list(avoid_groups or []), associated_drawer))

    def get_prizes(self):
        return list(self.prizes)

    def reorder_prizes(self, order):
        n = len(self.prizes)
        try:
            if sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
