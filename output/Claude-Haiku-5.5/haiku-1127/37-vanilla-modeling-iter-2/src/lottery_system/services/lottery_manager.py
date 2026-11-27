"""Lottery rule engine and draw execution."""

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager, Winner

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
FALLBACK_DRAWER = "Ma Jiaqi"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
CONSECUTIVE_THRESHOLD = 2


def _same(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


class LotteryManager:
    """Runs lottery draws while enforcing the lottery rules."""

    def __init__(self, users: list[User]):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results (True = contains Cheng Ru group member) of the most recent
        # draws by Chen Qixian / Jin Duo, at most CONSECUTIVE_THRESHOLD entries.
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()

    @property
    def winner_names(self) -> set[str]:
        return set(self._winner_names)

    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    @staticmethod
    def is_cheng_ru(user: User) -> bool:
        return _same(user.department, CHENG_RU_GROUP)

    def _fallback_active(self, prize: Prize) -> bool:
        drawer = prize.associated_drawer
        if not drawer or not _same(drawer, FALLBACK_DRAWER):
            return False
        if len(self.last_two_draw_results) < CONSECUTIVE_THRESHOLD:
            return False
        return not any(self.last_two_draw_results[-CONSECUTIVE_THRESHOLD:])

    def _compute_pool(self, prize: Prize) -> tuple[list[User], bool]:
        """Return (eligible users, whether the Cheng Ru protection was applied)."""
        available = [u for u in self.users if u.name not in self._winner_names]
        drawer = prize.associated_drawer

        # Special rule: Li Bin only filters previous winners.
        if drawer and _same(drawer, LI_BIN):
            return available, False

        # Fallback: force Cheng Ru group members for Ma Jiaqi.
        if self._fallback_active(prize):
            forced = [u for u in available if self.is_cheng_ru(u)]
            if forced:
                return forced, True

        avoid = {g.strip().casefold() for g in prize.avoid_groups}
        pool = [u for u in available if u.department.strip().casefold() not in avoid]
        return pool, False

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        return self._compute_pool(prize)[0]

    def describe_rule(self, prize: Prize) -> str:
        parts: list[str] = []
        drawer = prize.associated_drawer
        if drawer and _same(drawer, LI_BIN):
            parts.append("previous winners excluded only (avoidance groups not applied)")
        else:
            parts.append("previous winners excluded")
            if prize.avoid_groups:
                parts.append("avoidance groups: " + ", ".join(prize.avoid_groups))
            if drawer and _same(drawer, FALLBACK_DRAWER):
                parts.append("Cheng Ru Group protection applies if Chen Qixian/Jin Duo "
                             "produced no Cheng Ru Group winner in their last two draws")
        if drawer:
            parts.append(f"lottery person: {drawer}")
        return "; ".join(parts)

    def draw(self, prize: Prize) -> User | None:
        pool, forced = self._compute_pool(prize)
        if not pool:
            return None
        winner_user = random.choice(pool)
        self._winner_names.add(winner_user.name)
        self.result_manager.add_winner(winner_user, prize)

        drawer = prize.associated_drawer
        if drawer and any(_same(drawer, d) for d in TRACKED_DRAWERS):
            self.last_two_draw_results.append(self.is_cheng_ru(winner_user))
            self.last_two_draw_results = self.last_two_draw_results[-CONSECUTIVE_THRESHOLD:]
        elif forced:
            # Protection has been used; restart the consecutive-failure window.
            self.last_two_draw_results = []
        return winner_user

    def get_winner_records(self) -> list[Winner]:
        return self.result_manager.winners
