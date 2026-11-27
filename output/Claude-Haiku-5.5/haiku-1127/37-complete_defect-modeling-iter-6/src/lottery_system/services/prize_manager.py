"""Prize library management, avoidance configuration and ordering."""

from __future__ import annotations

from lottery_system.models import Prize, normalize_text


DEFAULT_PRIZES: list[tuple[str, int, str]] = [
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the ordered list of prizes for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize_text(name)
        for prize in self._prizes:
            if normalize_text(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize '{name}' already exists and was skipped")
                continue
            self._prizes.append(Prize(name=name, quantity=quantity, avoid_groups=[], associated_drawer=drawer))
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Add a custom prize. Raises ValueError on invalid input."""
        clean_name = " ".join(str(name or "").split())
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(clean_name) is not None:
            raise ValueError(f"Prize '{clean_name}' already exists.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(Prize(name=clean_name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer))

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        order[k] is the 1-based current position of the prize that should be
        placed at new position k + 1. Returns False if order is not a valid permutation.
        """
        count = len(self._prizes)
        try:
            values = list(order)
        except TypeError:
            return False
        if len(values) != count:
            return False
        if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
            return False
        if sorted(values) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in values]
        return True
