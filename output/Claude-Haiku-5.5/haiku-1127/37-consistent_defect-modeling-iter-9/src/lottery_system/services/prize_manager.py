"""Prize library management, avoidance rules and sequencing."""
from __future__ import annotations

from lottery_system.models import Prize

PRESET_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in PRESET_PRIZES:
            if any(p.name.lower() == name.lower() for p in self._prizes):
                continue
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"Cannot load preset prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize at the end of the sequence. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if any(p.name.lower() == clean_name.lower() for p in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")

        groups: list[str] = []
        for group in avoid_groups or []:
            group = group.strip()
            if group and group not in groups:
                groups.append(group)

        drawer = associated_drawer.strip() if associated_drawer else None
        drawer = drawer or None

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        ``order`` contains 1-based current positions; the i-th element is the
        current position of the prize that should be placed at position i in
        the new sequence. Returns False if the order is not a valid permutation.
        """
        count = len(self._prizes)
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
