"""Prize library management, avoidance configuration and ordering."""

from __future__ import annotations

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 6, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Append a prize to the end of the lottery order.

        Raises ValueError for an empty name, a non-positive quantity or a
        duplicate prize name.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        groups = list(dict.fromkeys(groups))
        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = associated_drawer.strip()

        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order.

        Returns False if `order` is not a permutation of all current positions.
        """
        n = len(self._prizes)
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in positions]
        return True
