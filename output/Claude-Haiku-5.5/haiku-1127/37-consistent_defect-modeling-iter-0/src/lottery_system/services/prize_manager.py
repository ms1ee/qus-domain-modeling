"""Prize library management and prize ordering."""

from lottery_system.models import Prize

PRESET_PRIZES = [
    ("Third Prize - Movie Tickets", 3, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 2, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
]


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


class PrizeManager:
    """Keeps the ordered prize library for the lottery."""

    def __init__(self) -> None:
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes. Returns a list of error messages."""
        errors: list[str] = []
        for name, quantity, drawer in PRESET_PRIZES:
            try:
                self.add_prize(name, quantity, None, drawer)
            except ValueError as exc:
                errors.append(str(exc))
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Add a prize to the end of the lottery sequence."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Prize name must not be empty.")
        name = name.strip()
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Quantity must be a positive integer.")
        if any(_norm(p.name) == _norm(name) for p in self._prizes):
            raise ValueError(f"Prize '{name}' already exists.")
        groups = [g.strip() for g in (avoid_groups or []) if g and g.strip()]
        drawer = associated_drawer.strip() if associated_drawer and associated_drawer.strip() else None
        prize = Prize(name, quantity, groups, drawer)
        self._prizes.append(prize)
        return prize

    def get_prizes(self) -> list[Prize]:
        """Return prizes in current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. order contains 1-based current positions in the new order."""
        n = len(self._prizes)
        try:
            ints = [int(x) for x in order]
        except (TypeError, ValueError):
            return False
        if sorted(ints) != list(range(1, n + 1)):
            return False
        self._prizes = [self._prizes[i - 1] for i in ints]
        return True
