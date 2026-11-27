"""Prize library management."""

from __future__ import annotations

from ..constants import DEFAULT_PRIZE_DATA
from ..models import Prize, normalize_text


def _clean_groups(groups) -> list[str]:
    """Strip, drop empties and de-duplicate group names (order preserved)."""
    cleaned: list[str] = []
    if not groups:
        return cleaned
    seen: set[str] = set()
    for group in groups:
        text = str(group).strip()
        key = normalize_text(text)
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


class PrizeManager:
    """Maintains the ordered list of prizes."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZE_DATA:
            try:
                self.add_prize(name, quantity, [], drawer)
            except ValueError as exc:
                errors.append(f"Cannot load preset prize '{name}': {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Append a new prize to the end of the lottery sequence."""
        prize_name = str(name or "").strip()
        if not prize_name:
            raise ValueError("prize name cannot be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if any(normalize_text(p.name) == normalize_text(prize_name) for p in self._prizes):
            raise ValueError(f"prize '{prize_name}' already exists")

        drawer = None
        if associated_drawer is not None and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()

        prize = Prize(prize_name, quantity, _clean_groups(avoid_groups), drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups) -> bool:
        """Replace the avoidance groups of the prize at 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].avoid_groups = _clean_groups(groups)
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if not isinstance(order, (list, tuple)) or len(order) != count:
            return False
        if any(isinstance(pos, bool) or not isinstance(pos, int) for pos in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in order]
        return True
