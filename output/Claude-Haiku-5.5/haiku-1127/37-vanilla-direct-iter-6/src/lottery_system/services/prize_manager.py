"""Prize library management and lottery sequence configuration."""

from __future__ import annotations

from lottery_system.models import Prize


DEFAULT_PRIZE_LIBRARY: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Maintains the ordered list of prizes for the current lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, groups, drawer in DEFAULT_PRIZE_LIBRARY:
            try:
                self.add_prize(name, quantity, list(groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(clean_name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups: list[str]) -> bool:
        """Set avoidance groups of the prize at 1-based position index."""
        if not 1 <= index <= len(self._prizes):
            return False
        self._prizes[index - 1].avoid_groups = [g.strip() for g in groups if g and g.strip()]
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """order: 1-based current positions, listed in the new sequence."""
        n = len(self._prizes)
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
