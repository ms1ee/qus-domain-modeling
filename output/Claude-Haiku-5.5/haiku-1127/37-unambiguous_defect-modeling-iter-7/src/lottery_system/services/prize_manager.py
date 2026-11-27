"""Prize library management and round ordering."""

import re

from lottery_system.constants import DEFAULT_PRIZES
from lottery_system.models import Prize

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3}
_CUSTOM_LEVEL_BASE = 100


def _level_from_name(name):
    match = re.match(r"\s*(first|second|third)\s+prize", name, re.IGNORECASE)
    if match:
        return _LEVEL_WORDS[match.group(1).lower()]
    return None


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        """Load the preset prize library. Returns a list of error messages."""
        errors = []
        for config in DEFAULT_PRIZES:
            try:
                self.add_prize(
                    config["name"],
                    config["quantity"],
                    list(config["avoid_groups"]),
                    config["associated_drawer"],
                )
                self._prizes[-1].is_preset = True
            except ValueError as exc:
                errors.append(f"Preset prize not loaded: {config['name']} ({exc})")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Add a prize at the end of the round order.

        Raises ValueError for an empty name, invalid quantity or duplicate name.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(existing.name == name for existing in self._prizes):
            raise ValueError(f"A prize named '{name}' already exists.")

        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        prize = Prize(name, quantity, groups, drawer)
        level = _level_from_name(name)
        prize.level = level if level is not None else _CUSTOM_LEVEL_BASE + len(self._prizes)
        prize.is_preset = False
        self._prizes.append(prize)
        self._refresh_sequence_numbers()

    def get_prizes(self):
        """Return prizes in current round order."""
        return list(self._prizes)

    def reorder_prizes(self, order):
        """Reorder prizes using 1-based current positions.

        ``order`` must contain every current position exactly once.
        Returns True on success, False otherwise.
        """
        try:
            normalized = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(normalized) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        self._refresh_sequence_numbers()
        return True

    def _refresh_sequence_numbers(self):
        for index, prize in enumerate(self._prizes, start=1):
            prize.sequence_number = index
