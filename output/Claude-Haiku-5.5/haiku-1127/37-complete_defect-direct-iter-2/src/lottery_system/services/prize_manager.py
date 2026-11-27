"""Prize library management, group avoidance configuration and ordering."""

from __future__ import annotations

from lottery_system.models import Prize

# Preset prize library: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 4, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Chen Qixian"),
    ("Fourth Prize - Team Snacks", 5, [], "Li Bin"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the ordered list of prizes for a lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"Prize '{name}' not added: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize at the end of the current order. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"a prize named '{clean_name}' already exists")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order.

        Returns True on success, False if `order` is not a permutation of all positions.
        """
        n = len(self._prizes)
        if n == 0 or len(order) != n:
            return False
        if set(order) != set(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
