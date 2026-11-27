"""Prize library management."""

from typing import List, Optional

from lottery_system.constants import normalize_text
from lottery_system.models import Prize


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    PRESET_PRIZES = [
        ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
        ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
        ("First Prize - 1 Day Annual Leave", 1, [], "Li Bin"),
    ]

    def __init__(self):
        self._prizes: List[Prize] = []

    def load_default_prizes(self) -> List[str]:
        """Load the preset prize library. Returns a list of error messages."""
        errors: List[str] = []
        for name, quantity, avoid_groups, drawer in self.PRESET_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Append a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(normalize_text(p.name) == normalize_text(clean_name) for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: List[str] = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer: Optional[str] = None
        if associated_drawer and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()

        self._prizes.append(Prize(clean_name, quantity, groups, drawer))

    def get_prizes(self) -> List[Prize]:
        """Return the prizes in the current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        total = len(self._prizes)
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, total + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True
