"""Prize library management, avoidance configuration and sequencing."""

from __future__ import annotations

from lottery_system.models import Prize, normalize


DEFAULT_PRIZES = (
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
)


class PrizeManager:
    """Keeps the ordered list of prizes for the lottery."""

    def __init__(self):
        self._prizes: list[Prize] = []

    def load_default_prizes(self) -> list[str]:
        """Add the preset prizes to the end of the current sequence."""
        errors: list[str] = []
        for name, quantity, drawer in DEFAULT_PRIZES:
            try:
                self.add_prize(name, quantity, None, drawer)
            except ValueError as exc:
                errors.append(f"Preset prize '{name}' skipped: {exc}")
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None) -> Prize:
        """Add a prize at the end of the sequence. Raises ValueError on invalid input."""
        clean_name = " ".join(str(name or "").split())
        if not clean_name:
            raise ValueError("prize name must not be empty")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        key = normalize(clean_name)
        if any(normalize(prize.name) == key for prize in self._prizes):
            raise ValueError(f"prize '{clean_name}' already exists")
        groups = self._clean_groups(avoid_groups)
        drawer = self._clean_text(associated_drawer)
        prize = Prize(name=clean_name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        self._prizes.append(prize)
        return prize

    def update_prize(self, index, avoid_groups=None, associated_drawer=None) -> None:
        """Replace avoidance groups and associated lottery person of the prize at a 0-based index."""
        if not 0 <= index < len(self._prizes):
            raise ValueError("prize index out of range")
        prize = self._prizes[index]
        prize.avoid_groups = self._clean_groups(avoid_groups)
        prize.associated_drawer = self._clean_text(associated_drawer)

    def get_prizes(self) -> list[Prize]:
        """Return prizes in the current lottery sequence."""
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """Reorder prizes. `order` holds 1-based current positions in the new order."""
        count = len(self._prizes)
        try:
            valid = sorted(order) == list(range(1, count + 1))
        except TypeError:
            return False
        if not valid or len(order) != count:
            return False
        self._prizes = [self._prizes[position - 1] for position in order]
        return True

    @staticmethod
    def _clean_groups(groups) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for group in groups or []:
            cleaned = " ".join(str(group).split())
            if cleaned and normalize(cleaned) not in seen:
                seen.add(normalize(cleaned))
                result.append(cleaned)
        return result

    @staticmethod
    def _clean_text(value) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(str(value).split())
        return cleaned or None
