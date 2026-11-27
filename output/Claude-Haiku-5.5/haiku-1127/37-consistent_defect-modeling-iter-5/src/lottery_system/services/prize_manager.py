"""Prize library management: preset prizes, custom prizes, avoidance groups and ordering."""
from lottery_system.data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    def __init__(self):
        self._prizes = []
        self._default_loaded = False

    def load_default_prizes(self):
        """Add the preset prize library. Returns a list of error messages."""
        if self._default_loaded:
            return ["Preset prizes have already been loaded"]
        for name, quantity, level in DEFAULT_PRIZES:
            self._prizes.append(Prize(name=name, quantity=quantity, level=level))
        self._default_loaded = True
        return []

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Add a custom prize at the end of the lottery sequence and return it."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer")
        if any(prize.name == name for prize in self._prizes):
            raise ValueError(f"A prize named '{name}' already exists")
        groups = []
        for group in avoid_groups or []:
            group = (group or "").strip()
            if group and group not in groups:
                groups.append(group)
        drawer = (associated_drawer or "").strip() or None
        prize = Prize(name=name, quantity=quantity, avoid_groups=groups,
                      associated_drawer=drawer, level=0)
        self._prizes.append(prize)
        return prize

    def get_prizes(self):
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def set_avoid_groups(self, index, groups):
        """Replace the avoidance groups of the prize at 0-based index."""
        prize = self._prizes[index]
        cleaned = []
        for group in groups or []:
            group = (group or "").strip()
            if group and group not in cleaned:
                cleaned.append(group)
        prize.avoid_groups = cleaned

    def set_associated_drawer(self, index, drawer):
        """Set the associated lottery person of the prize at 0-based index (None clears)."""
        prize = self._prizes[index]
        prize.associated_drawer = (drawer or "").strip() or None

    def reorder_prizes(self, order):
        """Reorder prizes. order holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
