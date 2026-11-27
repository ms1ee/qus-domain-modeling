"""Prize library management and lottery sequence ordering."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists and was skipped: {name}")
                continue
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Cannot add preset prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the end of the lottery sequence.

        Raises ValueError for an empty name, a non-positive quantity or a
        duplicate prize name.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name cannot be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if self._find(clean_name) is not None:
            raise ValueError(f"a prize named '{clean_name}' already exists")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = (group or "").strip()
            if cleaned and normalize(cleaned) not in {normalize(g) for g in groups}:
                groups.append(cleaned)

        drawer = (associated_drawer or "").strip() or None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        ``order`` contains 1-based current positions in the desired new order.
        It must be a permutation of 1..N; otherwise nothing changes and False
        is returned.
        """
        try:
            valid = sorted(order) == list(range(1, len(self._prizes) + 1))
        except TypeError:
            return False
        if not valid:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    def _find(self, name: str) -> Prize | None:
        key = normalize(name)
        for prize in self._prizes:
            if normalize(prize.name) == key:
                return prize
        return None
