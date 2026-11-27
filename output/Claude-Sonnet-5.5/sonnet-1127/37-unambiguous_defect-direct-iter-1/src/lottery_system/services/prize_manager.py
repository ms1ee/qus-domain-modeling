from typing import List

from ..models import Prize


class PrizeManager:
    def __init__(self):
        self.prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        errors: List[str] = []
        defaults = [
            ("Third Prize - Movie Tickets", 3, [], "Chen Qixian"),
            ("Second Prize - Shopping Cards", 2, [], "Jin Duo"),
            ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
        ]
        for n, q, a, d in defaults:
            try:
                self.add_prize(n, q, a, d)
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
        prize = Prize(name, quantity, list(avoid_groups or []), associated_drawer or None)
        self.prizes.append(prize)
        return prize

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
