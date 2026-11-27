"""Prize library management and round ordering."""

from lottery_system.models import Prize, normalize_text, same_text

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Manages the prize library and the lottery round sequence."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def find_prize(self, name: str) -> Prize | None:
        """Find a prize by name (case-insensitive)."""
        for prize in self._prizes:
            if same_text(prize.name, name):
                return prize
        return None

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize to the end of the round sequence."""
        clean_name = " ".join(str(name or "").split())
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if self.find_prize(clean_name) is not None:
            raise ValueError(f"Prize already exists: {clean_name}")

        groups = self._clean_groups(avoid_groups)
        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def set_avoid_groups(self, name: str, groups: list[str]) -> bool:
        """Replace the avoidance groups of an existing prize."""
        prize = self.find_prize(name)
        if prize is None:
            return False
        prize.avoid_groups = self._clean_groups(groups)
        return True

    def get_prizes(self) -> list[Prize]:
        """Return prizes in lottery round order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes.

        ``order`` contains 1-based current positions in the desired new order,
        e.g. [3, 1, 2] means the third prize becomes first, the first second,
        and the second third.
        """
        count = len(self._prizes)
        if not isinstance(order, list) or len(order) != count:
            return False
        if any(isinstance(item, bool) or not isinstance(item, int) for item in order):
            return False
        if sorted(order) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[index - 1] for index in order]
        return True

    @staticmethod
    def _clean_groups(groups: list[str] | None) -> list[str]:
        cleaned: list[str] = []
        for group in groups or []:
            text = " ".join(str(group).split())
            if text and not any(same_text(text, existing) for existing in cleaned):
                cleaned.append(text)
        return cleaned
