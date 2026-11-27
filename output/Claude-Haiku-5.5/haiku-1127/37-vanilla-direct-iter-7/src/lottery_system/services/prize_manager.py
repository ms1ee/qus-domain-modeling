from lottery_system.config import DEFAULT_PRIZES
from lottery_system.models import Prize


class PrizeManager:
    """Manages the prize library and the lottery round order."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = name.strip().casefold()
        for prize in self._prizes:
            if prize.name.strip().casefold() == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            if self._find(name) is not None:
                continue
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
            except ValueError as exc:
                errors.append(f"Failed to load '{name}': {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        """Add a prize at the end of the round order."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if self._find(clean_name) is not None:
            raise ValueError(f"A prize named '{clean_name}' already exists.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")

        groups: list[str] = []
        for group in avoid_groups or []:
            group_name = str(group).strip()
            if group_name and group_name not in groups:
                groups.append(group_name)

        drawer = associated_drawer.strip() if associated_drawer else None
        if drawer == "":
            drawer = None

        self._prizes.append(
            Prize(
                name=clean_name,
                quantity=quantity,
                avoid_groups=groups,
                associated_drawer=drawer,
            )
        )

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        try:
            positions = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        count = len(self._prizes)
        if sorted(positions) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[pos - 1] for pos in positions]
        return True
