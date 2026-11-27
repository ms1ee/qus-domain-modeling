"""Prize library management: preset prizes, custom prizes, avoidance groups and ordering."""

from __future__ import annotations

from lottery_system.models import Prize, normalize_text

DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Ma Jiaqi"),
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
        """Add a prize to the end of the lottery sequence."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Prize name must not be empty.")
        clean_name = " ".join(name.split())
        key = normalize_text(clean_name)
        if any(normalize_text(p.name) == key for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")

        groups: list[str] = []
        seen_groups: set[str] = set()
        for group in avoid_groups or []:
            if not isinstance(group, str):
                continue
            display = " ".join(group.split())
            if display and normalize_text(display) not in seen_groups:
                seen_groups.add(normalize_text(display))
                groups.append(display)

        drawer: str | None = None
        if associated_drawer is not None and str(associated_drawer).strip():
            drawer = " ".join(str(associated_drawer).split())

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order (a shallow copy of the list)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            positions = list(order)
        except TypeError:
            return False
        if not all(isinstance(p, int) and not isinstance(p, bool) for p in positions):
            return False
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[p - 1] for p in positions]
        return True
