"""Prize library management."""

from ..config import DEFAULT_PRIZES
from ..models import Prize, normalize_key


class PrizeManager:
    """Manages the ordered prize library. Starts with no prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize_key(name)
        for prize in self._prizes:
            if normalize_key(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for spec in DEFAULT_PRIZES:
            if self._find(spec["name"]) is not None:
                errors.append(f"Prize '{spec['name']}' already exists, skipped.")
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

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        name = (name or "").strip()
        if not name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if self._find(name) is not None:
            raise ValueError(f"prize '{name}' already exists")

        groups = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)

        drawer = associated_drawer.strip() if associated_drawer else None
        drawer = drawer or None

        prize = Prize(
            name=name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def update_avoid_groups(self, name, avoid_groups) -> bool:
        prize = self._find(name)
        if prize is None:
            return False
        groups = []
        for group in avoid_groups or []:
            cleaned = str(group).strip()
            if cleaned and cleaned not in groups:
                groups.append(cleaned)
        prize.avoid_groups = groups
        return True

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        n = len(self._prizes)
        if not isinstance(order, (list, tuple)) or len(order) != n:
            return False
        if any(isinstance(x, bool) or not isinstance(x, int) for x in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
