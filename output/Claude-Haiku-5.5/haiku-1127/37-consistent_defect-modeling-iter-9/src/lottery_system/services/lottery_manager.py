"""Lottery rule engine: eligibility filtering, special rules and fallback."""
from __future__ import annotations

import random

from lottery_system.models import (
    CHENG_RU_GROUP,
    FALLBACK_DRAWERS,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)


def _is_cheng_ru(user: User) -> bool:
    return user.department.strip().lower() == CHENG_RU_GROUP.lower()


class LotteryManager:
    """Performs draws while enforcing the lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Results (True = winner belongs to Cheng Ru Group) of the most recent
        # draws made by Chen Qixian and Jin Duo, at most two entries.
        self.last_two_draw_results: list[bool] = []

    def _available_users(self) -> list[User]:
        """Users who have not won any prize yet (anti-duplication)."""
        return [u for u in self._users if u.name not in self._winner_names]

    def _fallback_active(self) -> bool:
        """True when the last two results of Chen Qixian/Jin Duo contain no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users that may be drawn for the given prize."""
        available = self._available_users()

        # Special rule: Li Bin only filters previous winners.
        if prize.associated_drawer == LI_BIN:
            return available

        # Fallback rule: Ma Jiaqi's prize is limited to Cheng Ru Group members.
        if prize.associated_drawer == MA_JIAQI and self._fallback_active():
            protected = [u for u in available if _is_cheng_ru(u)]
            if protected:
                return protected

        # Avoidance groups: members remain eligible but are drawn only after others.
        avoid = {g.strip().lower() for g in prize.avoid_groups}
        preferred = [u for u in available if u.department.strip().lower() not in avoid]
        if preferred:
            return preferred
        return [u for u in available if u.department.strip().lower() in avoid]

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None when no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_names.add(winner.name)
        if prize.associated_drawer in FALLBACK_DRAWERS:
            self.last_two_draw_results.append(_is_cheng_ru(winner))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner
