from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize library and the lottery round sequence."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, avoid, drawer in DEFAULT_PRIZE_SPECS:
            try:
                self.add_prize(name, quantity, avoid, drawer)
            except ValueError as exc:
                errors.append(f"Default prize '{name}': {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if any(p.name == clean_name for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        unique_groups = list(dict.fromkeys(groups))
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=unique_groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes; `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            if len(order) != count or sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[index - 1] for index in order]
        return True
