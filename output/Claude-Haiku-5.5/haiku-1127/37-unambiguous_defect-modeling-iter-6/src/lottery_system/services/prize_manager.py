"""Prize library management."""
from __future__ import annotations

from lottery_system.models import Prize

PRESET_PRIZES: list[dict] = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 6,
        "avoid_groups": [],
        "associated_drawer": "Chen Qixian",
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 4,
        "avoid_groups": [],
        "associated_drawer": "Jin Duo",
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 2,
        "avoid_groups": [],
        "associated_drawer": "Ma Jiaqi",
    },
]


def _clean_groups(groups) -> list[str]:
    """Strip, drop empties and remove duplicates (case-insensitive) keeping order."""
    if not groups:
        return []
    if isinstance(groups, str):
        groups = groups.split(",")
    cleaned: list[str] = []
    seen: set[str] = set()
    for group in groups:
        text = str(group).strip()
        if not text:
            continue
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


class PrizeManager:
    """Keeps the ordered list of prizes configured for the event."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for preset in PRESET_PRIZES:
            if self._find(preset["name"]) is not None:
                errors.append(f"Prize already exists, skipped: {preset['name']}")
                continue
            self.add_prize(
                preset["name"],
                preset["quantity"],
                preset["avoid_groups"],
                preset["associated_drawer"],
            )
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Add a custom or preset prize at the end of the sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize already exists: {clean_name}")

        drawer = None
        if associated_drawer and str(associated_drawer).strip():
            drawer = str(associated_drawer).strip()

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=_clean_groups(avoid_groups),
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def set_avoid_groups(self, name: str, groups) -> bool:
        """Replace the avoidance groups of the named prize."""
        prize = self._find(name)
        if prize is None:
            return False
        prize.avoid_groups = _clean_groups(groups)
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. ``order`` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            normalized = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(normalized) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        return True

    def _find(self, name: str) -> Prize | None:
        key = name.strip().casefold()
        for prize in self._prizes:
            if prize.name.casefold() == key:
                return prize
        return None
