"""Prize library management and ordering."""

from __future__ import annotations

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int, str | None]] = [
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Presets already present are skipped."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if any(prize.name == name for prize in self._prizes):
                continue
            try:
                self.add_prize(name, quantity, [], drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name cannot be empty")
        if not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")
        drawer = (associated_drawer or "").strip() or None
        groups = list(dict.fromkeys(avoid_groups or []))
        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def update_prize(
        self,
        index: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> bool:
        """Update avoidance groups and lottery person of the prize at a 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        prize = self._prizes[index]
        prize.avoid_groups = list(dict.fromkeys(avoid_groups or []))
        prize.associated_drawer = (associated_drawer or "").strip() or None
        return True

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if not all(isinstance(pos, int) for pos in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in order]
        return True
