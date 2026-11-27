"""Prize library management and ordering."""
from lottery_system.default_data import DEFAULT_PRIZE_RECORDS
from lottery_system.models import Prize
from lottery_system.utils import normalize_text


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZE_RECORDS:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"Prize '{name}' not loaded: {exc}")
        return errors

    def add_prize(self, name: str, quantity: int, avoid_groups: list[str] | None = None,
                  associated_drawer: str | None = None) -> None:
        """Append a prize. Raises ValueError on invalid input."""
        clean_name = " ".join((name or "").split())
        if not clean_name:
            raise ValueError("prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer.")
        key = normalize_text(clean_name)
        if any(normalize_text(prize.name) == key for prize in self._prizes):
            raise ValueError(f"a prize named '{clean_name}' already exists.")

        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups or []:
            cleaned = " ".join(str(group).split())
            if cleaned and normalize_text(cleaned) not in seen:
                seen.add(normalize_text(cleaned))
                groups.append(cleaned)

        drawer = " ".join(associated_drawer.split()) if associated_drawer else None
        self._prizes.append(Prize(clean_name, quantity, groups, drawer or None))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if len(positions) != count or sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True
