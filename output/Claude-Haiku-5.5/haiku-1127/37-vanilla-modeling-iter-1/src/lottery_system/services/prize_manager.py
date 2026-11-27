"""Prize library management and round ordering."""
from __future__ import annotations

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 10),
    ("Second Prize - Shopping Cards", 5),
    ("First Prize - 1 Day Annual Leave", 2),
]


class PrizeManager:
    """Stores prizes and the lottery round sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = name.strip().casefold()
        for prize in self._prizes:
            if prize.name.casefold() == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists, skipped.")
                continue
            self._prizes.append(Prize(name, quantity))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a custom prize at the end of the round sequence.

        Raises ValueError for an empty name, a non-positive quantity or a
        duplicate name.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the
        new order and must be a permutation of 1..n."""
        count = len(self._prizes)
        try:
            is_permutation = sorted(order) == list(range(1, count + 1))
        except TypeError:
            return False
        if not is_permutation:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
