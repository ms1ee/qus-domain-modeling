"""Prize library management, group avoidance configuration and sequencing."""

from __future__ import annotations

from ..models import Prize, normalize

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"Cannot load default prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a prize to the end of the lottery sequence."""
        clean_name = " ".join(str(name or "").split())
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        key = normalize(clean_name)
        if any(normalize(p.name) == key for p in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")

        groups: list[str] = []
        for group in avoid_groups or []:
            group_name = " ".join(str(group).split())
            if group_name and group_name not in groups:
                groups.append(group_name)

        drawer = " ".join(str(associated_drawer).split()) if associated_drawer else None
        if not drawer:
            drawer = None

        prize = Prize(name=clean_name, quantity=quantity, avoid_groups=groups,
                      associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        n = len(self._prizes)
        try:
            indexes = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if len(indexes) != n or sorted(indexes) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in indexes]
        return True
