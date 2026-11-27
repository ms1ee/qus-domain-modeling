from __future__ import annotations

from lottery_system.models import Prize


PRESET_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 10),
    ("Second Prize - Shopping Cards", 5),
    ("First Prize - 1 Day Annual Leave", 2),
]


class PrizeManager:
    """Manages the prize library and the lottery sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _has_name(self, name: str) -> bool:
        key = name.strip().casefold()
        return any(prize.name.strip().casefold() == key for prize in self._prizes)

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns error messages for presets that could not be added."""
        errors: list[str] = []
        for name, quantity in PRESET_PRIZES:
            if self._has_name(name):
                errors.append(f"Prize already exists, skipped: '{name}'")
                continue
            self.add_prize(name, quantity)
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the library. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._has_name(clean_name):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            g = str(group).strip()
            if g and g not in groups:
                groups.append(g)

        drawer = associated_drawer.strip() if associated_drawer else None
        if drawer == "":
            drawer = None

        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        n = len(self._prizes)
        if len(order) != n:
            return False
        if not all(isinstance(i, int) and not isinstance(i, bool) for i in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
