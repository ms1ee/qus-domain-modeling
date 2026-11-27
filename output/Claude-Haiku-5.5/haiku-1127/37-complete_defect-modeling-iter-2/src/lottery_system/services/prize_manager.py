"""Prize library management, avoidance configuration and ordering."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, MA_JIAQI, Prize

DEFAULT_PRIZES: list[tuple[str, int, str]] = [
    ("Third Prize - Movie Tickets", 5, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 3, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
]


class PrizeManager:
    """Manages the ordered list of prizes for the event."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, associated_drawer=drawer)
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
        """Append a new prize. Raises ValueError on invalid input."""
        name = (name or "").strip()
        if not name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if any(prize.name == name for prize in self._prizes):
            raise ValueError(f"prize '{name}' already exists")
        drawer = associated_drawer.strip() if associated_drawer else None
        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=list(avoid_groups) if avoid_groups else [],
            associated_drawer=drawer or None,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
