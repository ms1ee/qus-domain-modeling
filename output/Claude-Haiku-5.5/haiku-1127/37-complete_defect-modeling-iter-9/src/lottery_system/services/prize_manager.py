"""Prize library management: presets, custom prizes, ordering."""

from lottery_system.models import Prize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, "Ma Jiaqi"),
]


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, [], drawer)
            except ValueError as error:
                errors.append(str(error))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(p.name.lower() == clean_name.lower() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        groups = list(dict.fromkeys(groups))
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes; order contains 1-based current positions in the new order."""
        try:
            if not all(isinstance(i, int) and not isinstance(i, bool) for i in order):
                return False
        except TypeError:
            return False
        if sorted(order) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
