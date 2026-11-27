"""Prize library management and prize ordering."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI, Prize

DEFAULT_PRIZE_PRESETS: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], None),
    ("Second Prize - Shopping Cards", 5, [], CHEN_QIXIAN),
    ("First Prize - 1 Day Annual Leave", 2, [], LI_BIN),
    ("Technology Department Exclusive Coupon", 3, ["Product Department"], JIN_DUO),
    ("Cheng Ru Group Special Gift", 2, ["Technology Department"], MA_JIAQI),
]


class PrizeManager:
    """Manages the ordered list of prizes."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages (empty on success)."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZE_PRESETS:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> None:
        """Append a prize to the end of the lottery sequence.

        Raises ValueError if the input is invalid.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        groups: list[str] = []
        for group in avoid_groups or []:
            text = (group or "").strip()
            if text and text not in groups:
                groups.append(text)

        drawer = (associated_drawer or "").strip() or None
        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order.

        Returns True on success, False if `order` is not a permutation of 1..n.
        """
        n = len(self._prizes)
        try:
            if len(order) != n or sorted(order) != list(range(1, n + 1)):
                return False
        except TypeError:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
