"""Prize library management and round ordering."""

from lottery_system import default_data
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes for lottery rounds."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in default_data.DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Append a prize to the end of the round sequence.

        Raises ValueError for an empty name, duplicate name or invalid quantity.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(p.name.casefold() == name.casefold() for p in self._prizes):
            raise ValueError(f"A prize named '{name}' already exists.")

        try:
            quantity_value = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Quantity must be a whole number.") from None
        if quantity_value < 1:
            raise ValueError("Quantity must be at least 1.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned.casefold() not in {g.casefold() for g in groups}:
                groups.append(cleaned)

        drawer = associated_drawer.strip() if associated_drawer else ""
        self._prizes.append(
            Prize(name, quantity_value, groups, drawer if drawer else None)
        )

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes using 1-based current positions in the new order.

        Returns False if the order is not a permutation of 1..N.
        """
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True
