"""Prize library management: presets, custom prizes, rules and ordering."""

from __future__ import annotations

from lottery_system.models import Prize, normalize


DEFAULT_PRIZES: list[tuple[str, int, str]] = [
    ("Third Prize - Movie Tickets", 3, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
]


class PrizeManager:
    """Maintains the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize(name)
        for prize in self._prizes:
            if normalize(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages, if any."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists and was skipped: {name}")
                continue
            self._prizes.append(
                Prize(name=name, quantity=quantity, avoid_groups=[], associated_drawer=drawer)
            )
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a custom prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize already exists: {clean_name}")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")

        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and normalize(cleaned) not in seen:
                seen.add(normalize(cleaned))
                groups.append(cleaned)

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def set_avoid_groups(self, name: str, avoid_groups: list[str]) -> bool:
        """Replace the avoidance groups of an existing prize."""
        prize = self._find(name)
        if prize is None:
            return False
        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups:
            cleaned = str(group).strip()
            if cleaned and normalize(cleaned) not in seen:
                seen.add(normalize(cleaned))
                groups.append(cleaned)
        prize.avoid_groups = groups
        return True

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        `order` contains 1-based current positions in the desired new order.
        Returns False if it is not a permutation of all current positions.
        """
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if not all(isinstance(item, int) and not isinstance(item, bool) for item in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
