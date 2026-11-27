from typing import List, Optional

from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        presets = [
            ("Third Prize - Movie Tickets", 3),
            ("Second Prize - Shopping Cards", 2),
            ("First Prize - 1 Day Annual Leave", 1),
        ]
        for name, qty in presets:
            try:
                self.add_prize(name, qty)
            except Exception as e:
                errors.append(str(e))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        if not name or quantity is None or int(quantity) <= 0:
            raise ValueError("Invalid prize name or quantity")
        p = Prize(name, int(quantity), list(avoid_groups or []), associated_drawer or None)
        self.prizes.append(p)
        return p

    def get_prizes(self) -> List[Prize]:
        return list(self.prizes)

    def reorder_prizes(self, order: List[int]) -> bool:
        n = len(self.prizes)
        try:
            order = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self.prizes = [self.prizes[i - 1] for i in order]
        return True
