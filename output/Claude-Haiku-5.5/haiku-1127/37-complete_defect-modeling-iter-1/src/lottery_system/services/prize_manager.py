"""Prize library management, group avoidance configuration and ordering."""

from lottery_system.models import Prize, normalize_text

DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 8, [], "Li Bin"),
    ("Second Prize - Shopping Cards", 4, ["Product Department"], "Chen Qixian"),
    ("First Prize - 1 Day Annual Leave", 2, ["Technology Department"], "Ma Jiaqi"),
]


class PrizeManager:
    """Manages the ordered list of prizes for a lottery session."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Load the preset prize library. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, avoid_groups, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, list(avoid_groups), drawer)
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
        """Append a prize to the end of the lottery sequence."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if any(normalize_text(p.name) == normalize_text(clean_name) for p in self._prizes):
            raise ValueError(f"A prize named '{clean_name}' already exists.")

        cleaned_groups: list[str] = []
        for group in avoid_groups or []:
            group_name = str(group).strip()
            if group_name and normalize_text(group_name) not in {
                normalize_text(g) for g in cleaned_groups
            }:
                cleaned_groups.append(group_name)

        drawer = (associated_drawer or "").strip() or None
        prize = Prize(
            name=clean_name,
            quantity=quantity,
            avoid_groups=cleaned_groups,
            associated_drawer=drawer,
        )
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        n = len(self._prizes)
        if not isinstance(order, list) or len(order) != n:
            return False
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in order):
            return False
        if sorted(order) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True
