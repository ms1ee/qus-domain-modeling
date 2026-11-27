"""Prize library management: presets, custom prizes, avoidance groups, ordering."""
from __future__ import annotations

from lottery_system.models import Prize

PRESET_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Li Bin"),
    ("Second Prize - Shopping Cards", 3, [], "Chen Qixian"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Jin Duo"),
]


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, groups, drawer in PRESET_PRIZES:
            try:
                self.add_prize(name, quantity, groups, drawer)
            except ValueError as exc:
                errors.append(f"Prize '{name}': {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Add a prize at the end of the current sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if any(p.name == clean_name for p in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")
        groups = list(dict.fromkeys(avoid_groups or []))
        drawer = associated_drawer.strip() if associated_drawer else None
        drawer = drawer or None
        prize = Prize(name=clean_name, quantity=quantity, avoid_groups=groups,
                      associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def set_avoid_groups(self, prize_name: str, groups: list[str]) -> bool:
        """Replace the avoidance groups of the named prize."""
        for prize in self._prizes:
            if prize.name == prize_name:
                prize.avoid_groups = list(dict.fromkeys(groups or []))
                return True
        return False

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order."""
        try:
            positions = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        total = len(self._prizes)
        if sorted(positions) != list(range(1, total + 1)):
            return False
        self._prizes = [self._prizes[p - 1] for p in positions]
        return True
