"""Prize library management."""

import re

from lottery_system import config
from lottery_system.models import Prize

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_LEVEL_RE = re.compile(r"\s*(first|second|third|fourth|fifth)\b", re.IGNORECASE)


def infer_level(name):
    """Infer prize level from the leading word of the name (First = 1 ...)."""
    match = _LEVEL_RE.match(name or "")
    if match:
        return _LEVEL_WORDS[match.group(1).lower()]
    return 99


class PrizeManager:
    """Manages prizes and their lottery order. Starts with no prizes."""

    def __init__(self):
        self._prizes = []

    def load_default_prizes(self):
        """Add the preset prize library. Returns a list of error messages."""
        errors = []
        for name, quantity, drawer in config.DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, None, drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if any(prize.name == name for prize in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(
            Prize(
                name=name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
                level=infer_level(name),
            )
        )

    def get_prizes(self):
        return list(self._prizes)

    def reorder_prizes(self, order):
        """Reorder prizes. order contains 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            items = list(order)
        except TypeError:
            return False
        if len(items) != count:
            return False
        if any(isinstance(item, bool) or not isinstance(item, int) for item in items):
            return False
        if set(items) != set(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in items]
        return True
