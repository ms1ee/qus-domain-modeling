"""Prize library management: presets, custom prizes, and ordering."""
from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZE_SPECS
from lottery_system.models import Prize, normalize


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages for skipped prizes."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZE_SPECS:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"Skipped preset prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        key = normalize(clean_name)
        if any(normalize(p.name) == key for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            text = str(group).strip()
            if text and text not in groups:
                groups.append(text)

        drawer = associated_drawer.strip() if associated_drawer else None
        if not drawer:
            drawer = None

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            is_permutation = sorted(order) == list(range(1, len(self._prizes) + 1))
        except TypeError:
            return False
        if not is_permutation:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
