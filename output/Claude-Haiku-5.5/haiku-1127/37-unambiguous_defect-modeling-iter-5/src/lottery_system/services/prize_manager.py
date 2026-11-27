"""Prize library management: presets, custom prizes, ordering."""

from __future__ import annotations

import re

from lottery_system.constants import (
    CHEN_QIXIAN,
    JIN_DUO,
    LEVEL_CUSTOM,
    LEVEL_FIRST,
    LEVEL_SECOND,
    LEVEL_THIRD,
    MA_JIAQI,
)
from lottery_system.models import Prize

# (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 3, [], CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 2, [], JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, [], MA_JIAQI),
]


class PrizeManager:
    """Manages the prize library and the lottery round order."""

    _LEVEL_PATTERN = re.compile(r"^\s*(first|second|third)\b", re.IGNORECASE)
    _LEVELS = {"first": LEVEL_FIRST, "second": LEVEL_SECOND, "third": LEVEL_THIRD}

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns a list of error messages."""
        if any(prize.is_preset for prize in self._prizes):
            return ["Preset prizes have already been loaded."]
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            prize = Prize(
                name=name,
                quantity=quantity,
                avoid_groups=list(avoid_groups),
                associated_drawer=drawer,
                level=self._infer_level(name),
                is_preset=True,
            )
            self._append(prize)
        return []

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a custom prize to the end of the lottery sequence."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=list(avoid_groups or []),
            associated_drawer=associated_drawer or None,
            level=self._infer_level(name),
            is_preset=False,
        )
        self._append(prize)

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            positions = [int(value) for value in order]
        except (TypeError, ValueError):
            return False
        count = len(self._prizes)
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        for index, prize in enumerate(self._prizes, start=1):
            prize.sequence_number = index
        return True

    def _append(self, prize: Prize) -> None:
        self._prizes.append(prize)
        prize.sequence_number = len(self._prizes)

    def _infer_level(self, name: str) -> int:
        match = self._LEVEL_PATTERN.match(name)
        if match:
            return self._LEVELS[match.group(1).lower()]
        return LEVEL_CUSTOM
