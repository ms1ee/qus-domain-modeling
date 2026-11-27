"""Prize library management."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        for prize in self._prizes:
            if prize.name == name:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid, drawer in DEFAULT_PRIZE_SPECS:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists, skipped")
                continue
            try:
                self.add_prize(name, quantity, list(avoid), drawer)
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
        """Add a prize at the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = (group or "").strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in new order."""
        count = len(self._prizes)
        try:
            valid = sorted(order) == list(range(1, count + 1))
        except TypeError:
            return False
        if not valid:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
