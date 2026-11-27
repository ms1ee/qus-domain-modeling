"""Prize library management and prize ordering."""

from lottery_system.models import Prize, normalize_text

# (name, quantity, associated lottery person)
_PRESET_PRIZES = (
    ("Third Prize - Movie Tickets", 6, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 4, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, "Ma Jiaqi"),
)


class PrizeManager:
    def __init__(self):
        self._prizes: list[Prize] = []

    def _find(self, name: str) -> Prize | None:
        key = normalize_text(name)
        for prize in self._prizes:
            if normalize_text(prize.name) == key:
                return prize
        return None

    def load_default_prizes(self) -> list[str]:
        errors: list[str] = []
        for name, quantity, drawer in _PRESET_PRIZES:
            if self._find(name) is not None:
                errors.append(f"Prize already exists, skipped: {name}")
                continue
            self._prizes.append(
                Prize(name=name, quantity=quantity, avoid_groups=[], associated_drawer=drawer)
            )
        return errors

    def add_prize(self, name, quantity, avoid_groups=None, associated_drawer=None):
        name = (name or "").strip()
        if not name:
            raise ValueError("Prize name cannot be empty.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Prize quantity must be a positive integer.")
        if self._find(name) is not None:
            raise ValueError(f"Prize already exists: {name}")

        groups: list[str] = []
        seen: set[str] = set()
        for group in avoid_groups or []:
            group = str(group).strip()
            key = normalize_text(group)
            if group and key not in seen:
                seen.add(key)
                groups.append(group)

        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        drawer = drawer or None

        self._prizes.append(
            Prize(name=name, quantity=quantity, avoid_groups=groups, associated_drawer=drawer)
        )

    def get_prizes(self) -> list[Prize]:
        return list(self._prizes)

    def reorder_prizes(self, order: list[int]) -> bool:
        """order[k] is the 1-based current position of the prize placed at new position k+1."""
        count = len(self._prizes)
        try:
            values = [int(item) for item in order]
        except (TypeError, ValueError):
            return False
        if sorted(values) != list(range(1, count + 1)):
            return False
        self._prizes = [self._prizes[value - 1] for value in values]
        return True
