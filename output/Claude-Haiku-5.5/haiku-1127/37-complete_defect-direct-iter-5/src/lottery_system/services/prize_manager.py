"""Prize library management and lottery sequence control."""

from lottery_system.models import Prize

DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prize library. Returns error messages, if any."""
        errors: list[str] = []
        for name, quantity in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity)
            except ValueError as exc:
                errors.append(f"Default prize '{name}': {exc}")
        return errors

    def add_prize(
        self,
        name: str,
        quantity: int,
        avoid_groups: list[str] | None = None,
        associated_drawer: str | None = None,
    ) -> Prize:
        """Add a prize to the end of the sequence. Raises ValueError on invalid input."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(prize.name == clean_name for prize in self._prizes):
            raise ValueError(f"Prize '{clean_name}' already exists.")

        groups: list[str] = []
        for group in avoid_groups or []:
            group = (group or "").strip()
            if group and group not in groups:
                groups.append(group)

        drawer = None
        if associated_drawer and associated_drawer.strip():
            drawer = associated_drawer.strip()

        prize = Prize(clean_name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return the prizes in current lottery order."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            order_list = list(order)
        except TypeError:
            return False
        if not all(isinstance(index, int) and not isinstance(index, bool) for index in order_list):
            return False
        if sorted(order_list) != list(range(1, len(self._prizes) + 1)):
            return False
        self._prizes = [self._prizes[index - 1] for index in order_list]
        return True
