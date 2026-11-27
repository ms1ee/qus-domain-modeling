"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.constants import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User


class LotteryManager:
    """Draws winners while enforcing all lottery rules.

    last_two_draw_results: records, for the most recent draws by the lottery persons
    Chen Qixian and Jin Duo, whether the winner belonged to the Cheng Ru group.
    """

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self.last_two_draw_results: list[bool] = []

    @property
    def winner_names(self) -> set[str]:
        return set(self._winner_names)

    def is_fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection applies to Ma Jiaqi's draws when the last two
        Chen Qixian / Jin Duo results contain no Cheng Ru group members."""
        if prize.associated_drawer != MA_JIAQI:
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _get_available_users(self) -> list[User]:
        return [user for user in self._users if user.name not in self._winner_names]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Primary pool: non-winners, excluding the prize's avoidance groups.

        Special rules:
        - Li Bin: only previous winners are filtered (avoidance groups not applied).
        - Fallback active (Ma Jiaqi): pool forced to Cheng Ru group members.
        """
        available = self._get_available_users()
        if self.is_fallback_active(prize):
            forced = [user for user in available if user.department == CHENG_RU_GROUP]
            if forced:
                return forced
        if prize.associated_drawer == LI_BIN:
            return available
        avoid = set(prize.avoid_groups)
        return [user for user in available if user.department not in avoid]

    def _get_deferred_pool(self, prize: Prize) -> list[User]:
        """Avoidance-group members: still eligible, drawn only after other members."""
        if prize.associated_drawer == LI_BIN or not prize.avoid_groups:
            return []
        avoid = set(prize.avoid_groups)
        return [user for user in self._get_available_users() if user.department in avoid]

    def _get_eligible_pool_with_fallback(self, prize: Prize) -> list[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_deferred_pool(prize)
        return pool

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool_with_fallback(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_names.add(winner.name)
        self._record_draw(prize, winner)
        return winner

    def _record_draw(self, prize: Prize, winner: User) -> None:
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            self.last_two_draw_results.append(winner.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI:
            self.last_two_draw_results = []
