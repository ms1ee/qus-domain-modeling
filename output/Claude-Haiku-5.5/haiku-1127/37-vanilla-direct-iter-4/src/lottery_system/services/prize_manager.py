"""Prize library management and ordering."""

from lottery_system.config import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize


class PrizeManager:
    """Manages the prize library and the lottery round sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize(name)
        for prize in self._prizes:
            if normalize(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages for skipped items."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists and was skipped: {name}")
                continue
            self._prizes.append(Prize(name, quantity, [], drawer))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a custom prize. Raises ValueError on invalid input."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(name) is not None:
            raise ValueError(f"A prize named '{name}' already exists.")
        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(name, quantity, groups, drawer))

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            if len(order) != count or sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
