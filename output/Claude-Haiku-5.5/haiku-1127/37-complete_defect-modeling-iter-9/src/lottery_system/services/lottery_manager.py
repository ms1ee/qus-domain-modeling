"""Lottery rule engine: eligibility pools, fallback protection and drawing."""

import random

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
FALLBACK_DRAWER = "Ma Jiaqi"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
CHENG_RU_GROUP = "Cheng Ru Group"


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users):
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Results (True = contained Cheng Ru group member) of the most recent
        # draws by the tracked lottery persons, at most two entries.
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _norm(text: str) -> str:
        return (text or "").strip().lower()

    def _is_cheng_ru(self, user: User) -> bool:
        return self._norm(user.department) == self._norm(CHENG_RU_GROUP)

    def _is_fallback_active(self, prize: Prize) -> bool:
        return (
            prize.associated_drawer == FALLBACK_DRAWER
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        # Basic filtering: previous winners are always excluded.
        pool = [u for u in self._users if u.name not in self._winner_names]

        # Special rule for Li Bin: only previous winners are filtered.
        if prize.associated_drawer == SPECIAL_DRAWER:
            return pool

        # Fallback (Cheng Ru group protection): overrides avoidance groups.
        if self._is_fallback_active(prize):
            return [u for u in pool if self._is_cheng_ru(u)]

        avoided = {self._norm(g) for g in prize.avoid_groups}
        return [u for u in pool if self._norm(u.department) not in avoided]

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize; returns None when no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_names.add(winner.name)
        if prize.associated_drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(self._is_cheng_ru(winner))
            del self.last_two_draw_results[:-2]
        return winner
