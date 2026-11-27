"""Prize library management."""
from __future__ import annotations

from lottery_system.models import Prize

DEFAULT_PRIZES: list[dict] = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 5,
        "avoid_groups": [],
        "associated_drawer": "Chen Qixian",
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 3,
        "avoid_groups": [],
        "associated_drawer": "Jin Duo",
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 1,
        "avoid_groups": [],
        "associated_drawer": "Ma Jiaqi",
    },
]


class PrizeManager:
    """Manages the ordered prize library. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for spec in DEFAULT_PRIZES:
            try:
                self.add_prize(
                    name=spec["name"],
                    quantity=spec["quantity"],
                    avoid_groups=list(spec["avoid_groups"]),
                    associated_drawer=spec["associated_drawer"],
                )
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
        """Append a prize to the end of the lottery order and return it."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer else None
        if not drawer:
            drawer = None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order (a copy of the list)."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order.

        Returns True on success, False if `order` is not a permutation of positions.
        """
        count = len(self._prizes)
        try:
            if sorted(order) != list(range(1, count + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
