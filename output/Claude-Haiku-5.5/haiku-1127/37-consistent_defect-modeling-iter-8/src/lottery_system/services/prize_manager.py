"""Prize library management: presets, custom prizes, avoidance groups and ordering."""

from __future__ import annotations

from lottery_system.constants import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered list of prizes (order = lottery round sequence)."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, associated_drawer=drawer)
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
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = self._clean_groups(avoid_groups)
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(name=clean_name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def set_avoid_groups(self, prize_name: str, avoid_groups: list[str] | None) -> bool:
        for prize in self._prizes:
            if prize.name == prize_name:
                prize.avoid_groups = self._clean_groups(avoid_groups)
                return True
        return False

    def reorder_prizes(self, order: list[int]) -> bool:
        """order: 1-based current positions, listed in the new order."""
        count = len(self._prizes)
        try:
            normalized = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(normalized) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        return True

    @staticmethod
    def _clean_groups(groups: list[str] | None) -> list[str]:
        cleaned: list[str] = []
        for group in groups or []:
            if group is None:
                continue
            text = str(group).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned
