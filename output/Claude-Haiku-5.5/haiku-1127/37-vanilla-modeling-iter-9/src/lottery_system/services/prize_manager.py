"""Prize library management and sequencing."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, MA_JIAQI, Prize

DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 5, [], JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 2, [], MA_JIAQI),
]


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"Preset prize '{name}' not loaded: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a prize to the end of the sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(existing.name == name for existing in self._prizes):
            raise ValueError(f"A prize named '{name}' already exists.")
        drawer = associated_drawer.strip() if associated_drawer else None
        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=list(avoid_groups or []),
            associated_drawer=drawer or None,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            if sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
