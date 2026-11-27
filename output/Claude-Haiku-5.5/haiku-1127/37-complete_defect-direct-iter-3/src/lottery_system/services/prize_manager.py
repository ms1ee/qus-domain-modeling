"""Prize library management, avoidance configuration and ordering."""

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the end of the lottery sequence.

        Raises ValueError for an empty name, invalid quantity or duplicate name.
        """
        clean_name = " ".join((name or "").split())
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(normalize(p.name) == normalize(clean_name) for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery order."""
        return list(self._prizes)

    def set_avoid_groups(self, name: str, groups: list[str]) -> bool:
        """Replace the avoidance groups of a prize. Returns False if not found."""
        for prize in self._prizes:
            if normalize(prize.name) == normalize(name):
                prize.avoid_groups = [g.strip() for g in groups if g and g.strip()]
                return True
        return False

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        order: 1-based current positions, listed in the new order.
        Returns True if applied, False if order is not a permutation of 1..n.
        """
        n = len(self._prizes)
        try:
            if len(order) != n or set(order) != set(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[pos - 1] for pos in order]
        return True
