from lottery_system.models import Prize


DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], None),
]


class PrizeManager:
    """Manages the prize library and the lottery round order."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, avoid, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            self._prizes.append(Prize(name, quantity, list(avoid), drawer))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty.")
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(name) is not None:
            raise ValueError(f"Prize '{name}' already exists.")
        drawer = associated_drawer.strip() if associated_drawer else None
        self._prizes.append(
            Prize(
                name=name,
                quantity=quantity,
                avoid_groups=list(avoid_groups or []),
                associated_drawer=drawer or None,
            )
        )

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def get_prize_by_name(self, name) -> Prize | None:
        return self._find(name)

    def set_avoid_groups(self, prize_name, groups) -> bool:
        prize = self._find(prize_name)
        if prize is None:
            return False
        prize.avoid_groups = list(groups)
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        n = len(self._prizes)
        try:
            if sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True

    def _find(self, name) -> Prize | None:
        for prize in self._prizes:
            if prize.name == name:
                return prize
        return None
