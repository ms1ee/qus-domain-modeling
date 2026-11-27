"""Prize library management, avoidance configuration and ordering."""

from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for the event."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for spec in DEFAULT_PRIZE_SPECS:
            try:
                self.add_prize(
                    spec["name"],
                    spec["quantity"],
                    list(spec["avoid_groups"]),
                    spec["associated_drawer"],
                )
            except ValueError as exc:
                errors.append(f"{spec['name']}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Add a prize at the end of the lottery sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(p.name == name for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(name=name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        n = len(self._prizes)
        try:
            if sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
