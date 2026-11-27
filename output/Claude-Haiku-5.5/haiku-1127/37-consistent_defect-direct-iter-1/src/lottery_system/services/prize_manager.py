"""Prize library management, avoidance configuration and ordering."""

from __future__ import annotations

from lottery_system.models import Prize, normalize_text

DEFAULT_PRIZES_DATA: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]


def _clean_groups(groups: list[str] | None) -> list[str]:
    """Strip, deduplicate and drop empty avoidance group names."""
    result: list[str] = []
    seen: set[str] = set()
    for group in groups or []:
        text = str(group).strip()
        if not text:
            continue
        key = normalize_text(text)
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


class PrizeManager:
    """Maintains the ordered list of prizes for a lottery session."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES_DATA:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Cannot add default prize '{name}': {exc}")
        return errors

    def _find_duplicate(self, name: str) -> bool:
        key = normalize_text(name)
        return any(normalize_text(p.name) == key for p in self._prizes)

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("prize quantity must be a positive integer")
        if self._find_duplicate(clean_name):
            raise ValueError(f"prize '{clean_name}' already exists")
        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=_clean_groups(avoid_groups),
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order."""
        return list(self._prizes)

    def set_avoid_groups(self, index: int, groups: list[str]) -> bool:
        """Replace the avoidance groups of the prize at a 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].avoid_groups = _clean_groups(groups)
        return True

    def set_associated_drawer(self, index: int, drawer: str | None) -> bool:
        """Set the associated lottery person of the prize at a 0-based index."""
        if not 0 <= index < len(self._prizes):
            return False
        self._prizes[index].associated_drawer = (drawer or "").strip() or None
        return True

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        ``order`` contains 1-based current positions in the desired new order.
        Returns False if ``order`` is not a permutation of all positions.
        """
        count = len(self._prizes)
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in positions]
        return True
