"""Prize library management and lottery sequence ordering."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize list. Starts empty; prizes are kept in lottery order."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, avoid_groups, drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | str | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name must not be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(p.name.casefold() == clean_name.casefold() for p in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        if avoid_groups is None:
            raw_groups: list[str] = []
        elif isinstance(avoid_groups, str):
            raw_groups = avoid_groups.split(",")
        else:
            raw_groups = list(avoid_groups)

        groups: list[str] = []
        for group in raw_groups:
            group = group.strip()
            if group and group not in groups:
                groups.append(group)

        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None

        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. ``order`` holds 1-based current positions in the new order."""
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(positions) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in positions]
        return True
