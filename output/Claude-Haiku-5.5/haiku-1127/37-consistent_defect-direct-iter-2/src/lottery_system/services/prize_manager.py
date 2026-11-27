"""Prize library management: presets, custom prizes, avoidance rules and ordering."""
from __future__ import annotations

import re

from lottery_system.models import Prize


DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]

_SPLIT_RE = re.compile(r"[,;]")


def _clean_list(values) -> list[str]:
    """Strip, drop empties and remove duplicates while keeping order."""
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


class PrizeManager:
    """Manages the ordered prize library."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a new prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=_clean_list(avoid_groups),
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups: list[str]) -> bool:
        """Set avoidance groups of the prize at 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].avoid_groups = _clean_list(groups)
        return True

    def set_associated_drawer(self, index: int, drawer: str | None) -> bool:
        """Set the lottery person of the prize at 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].associated_drawer = (drawer or "").strip() or None
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if any(isinstance(p, bool) or not isinstance(p, int) for p in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    @staticmethod
    def parse_group_text(text: str) -> list[str]:
        """Parse a comma/semicolon separated text into a clean list."""
        return _clean_list(_SPLIT_RE.split(text or ""))
