"""Prize library management, avoidance groups and lottery order."""

from __future__ import annotations

from lottery_system.models import Prize, normalize

DEFAULT_PRIZES: list[dict] = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 10,
        "avoid_groups": [],
        "associated_drawer": "Chen Qixian",
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 5,
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


class PrizeManager:
    """Manages the ordered list of prizes for the event."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for spec in DEFAULT_PRIZES:
            try:
                self.add_prize(
                    spec["name"],
                    spec["quantity"],
                    list(spec["avoid_groups"]),
                    spec["associated_drawer"],
                )
            except ValueError as exc:
                errors.append(f"Default prize '{spec['name']}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Append a new prize. Raises ValueError on invalid input."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        if any(normalize(p.name) == normalize(name) for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            cleaned = (group or "").strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order holds 1-based current positions in the new order."""
        n = len(self._prizes)
        if not isinstance(order, list) or len(order) != n:
            return False
        if any(isinstance(i, bool) or not isinstance(i, int) for i in order):
            return False
        if set(order) != set(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in order]
        return True
