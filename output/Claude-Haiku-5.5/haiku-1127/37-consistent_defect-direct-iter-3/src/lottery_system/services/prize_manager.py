"""Prize library management, avoidance configuration and sequencing."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize, normalize_text


def _clean_groups(avoid_groups) -> list[str]:
    cleaned: list[str] = []
    for group in avoid_groups or []:
        if group is None:
            continue
        text = str(group).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _clean_drawer(associated_drawer: str | None) -> str | None:
    if associated_drawer is None:
        return None
    text = associated_drawer.strip()
    return text or None


class PrizeManager:
    """Manages the ordered prize list. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Append a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        if self.find_prize(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=_clean_groups(avoid_groups),
            associated_drawer=_clean_drawer(associated_drawer),
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def find_prize(self, name: str) -> Prize | None:
        key = normalize_text(name)
        for prize in self._prizes:
            if normalize_text(prize.name) == key:
                return prize
        return None

    def configure_prize(self, name: str, avoid_groups=None, associated_drawer=None) -> bool:
        """Update avoidance groups and lottery person of an existing prize."""
        prize = self.find_prize(name)
        if prize is None:
            return False
        prize.avoid_groups = _clean_groups(avoid_groups)
        prize.associated_drawer = _clean_drawer(associated_drawer)
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            if len(order) != count or sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
