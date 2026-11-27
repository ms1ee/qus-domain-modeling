"""Prize library management."""

from __future__ import annotations

import re

from lottery_system.constants import DEFAULT_PRIZES, ORDINAL_LEVELS
from lottery_system.models import Prize
from lottery_system.utils import normalize_text

_ORDINAL_PATTERN = re.compile(r"^\s*(first|second|third|fourth|fifth)\b", re.IGNORECASE)


class PrizeManager:
    """Manages the prize library and the lottery sequence of prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns error messages."""
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
        avoid_groups: list[str] | str | None = None,
        associated_drawer: str | None = None,
        level: int | None = None,
    ) -> Prize:
        """Add a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize already exists: {clean_name}")

        if isinstance(avoid_groups, str):
            avoid_groups = avoid_groups.split(",")
        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]

        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        if level is None:
            level = self._infer_level(clean_name)

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
            level=level,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. ``order`` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        if len(order) != count:
            return False
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True

    def _find(self, name: str) -> Prize | None:
        key = normalize_text(name)
        for prize in self._prizes:
            if normalize_text(prize.name) == key:
                return prize
        return None

    def _infer_level(self, name: str) -> int:
        match = _ORDINAL_PATTERN.match(name)
        if match:
            return ORDINAL_LEVELS[match.group(1).lower()]
        existing = [prize.level for prize in self._prizes]
        return max(existing + [0, len(DEFAULT_PRIZES)]) + 1
