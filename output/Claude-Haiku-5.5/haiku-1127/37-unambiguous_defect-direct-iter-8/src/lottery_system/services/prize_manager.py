"""Prize library management: presets, custom prizes, avoidance rules and ordering."""

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages (empty on success)."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a new prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer else None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer or None,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in lottery sequence (a copy of the list)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes using 1-based current positions in the new order.

        Example: with prizes [A, B, C], order [3, 1, 2] yields [C, A, B].
        Returns False if the order is not a permutation of 1..n.
        """
        n = len(self._prizes)
        try:
            valid = sorted(order) == list(range(1, n + 1))
        except TypeError:
            valid = False
        if not valid:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
