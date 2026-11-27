"""Prize library management and ordering."""

from __future__ import annotations

from lottery_system.config import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Maintains the ordered prize library. Starts empty."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        for prize in self._prizes:
            if prize.name == name:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages (empty on success)."""
        errors: list[str] = []
        for spec in DEFAULT_PRIZES:
            if self._find(spec["name"]) is not None:
                errors.append(f"Prize already exists, skipped: {spec['name']}")
                continue
            self._prizes.append(
                Prize(
                    name=spec["name"],
                    quantity=spec["quantity"],
                    avoid_groups=list(spec["avoid_groups"]),
                    associated_drawer=spec["associated_drawer"],
                )
            )
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a custom prize. Raises ValueError on invalid input."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name must not be empty.")
        if self._find(name) is not None:
            raise ValueError(f"Prize already exists: {name}")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = [group.strip() for group in (avoid_groups or []) if group and group.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        self._prizes.append(
            Prize(name=name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        )

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order.

        Returns False (and leaves the library unchanged) if order is not a
        permutation of 1..n.
        """
        count = len(self._prizes)
        try:
            normalized = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(normalized) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in normalized]
        return True
