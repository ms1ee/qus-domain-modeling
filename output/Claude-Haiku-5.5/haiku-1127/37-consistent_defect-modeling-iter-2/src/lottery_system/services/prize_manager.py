"""Prize library management and lottery sequence ordering."""

from __future__ import annotations

from lottery_system.models import Prize

PRESET_PRIZES: list[tuple[str, int, str]] = [
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
]

_LEVEL_WORDS: dict[str, int] = {"first": 1, "second": 2, "third": 3}
_CUSTOM_LEVEL_BASE = 1000


def _infer_level(name: str, index: int) -> int:
    """Preset prizes get their rank from the name; custom prizes rank after them."""
    words = name.split()
    first_word = words[0].casefold() if words else ""
    return _LEVEL_WORDS.get(first_word, _CUSTOM_LEVEL_BASE + index)


class PrizeManager:
    """Manages the prize library and the lottery sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages (empty on success)."""
        errors: list[str] = []
        for name, quantity, drawer in PRESET_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists: {name}")
                continue
            try:
                self.add_prize(name, quantity, [], drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize at the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name cannot be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if self._find(clean_name) is not None:
            raise ValueError(f"prize '{clean_name}' already exists")

        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        prize.level = _infer_level(clean_name, len(self._prizes))
        prize.sequence_number = len(self._prizes) + 1
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` contains 1-based current positions in the new order."""
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if any(isinstance(item, bool) or not isinstance(item, int) for item in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        for index, prize in enumerate(self._prizes, start=1):
            prize.sequence_number = index
        return True

    def _find(self, name: str) -> Prize | None:
        target = name.strip().casefold()
        for prize in self._prizes:
            if prize.name.casefold() == target:
                return prize
        return None
