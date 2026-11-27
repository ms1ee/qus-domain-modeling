"""Prize library management, rule configuration and ordering."""

from __future__ import annotations

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages for skipped prizes."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
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
        """Append a prize. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"Prize '{clean_name}': quantity must be a positive integer.")
        if any(existing.name.casefold() == clean_name.casefold() for existing in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = (associated_drawer or "").strip() or None
        prize = Prize(name=clean_name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def set_rules(
        self,
        index: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> bool:
        """Update avoidance groups and associated lottery person of the prize at a 0-based index."""
        if index < 0 or index >= len(self._prizes):
            return False
        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = (associated_drawer or "").strip() or None
        prize = self._prizes[index]
        prize.avoid_groups = groups
        prize.associated_drawer = drawer
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            if sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
