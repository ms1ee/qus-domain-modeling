"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)


class LotteryManager:
    """Draws winners while enforcing the lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users = list(users)
        self._winner_names: set[str] = set()
        self._rng = rng or random.Random()
        # Whether each of the most recent draws by Chen Qixian / Jin Duo contained
        # at least one Cheng Ru group member (max length 2).
        self.last_two_draw_results: list[bool] = []

    def is_fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru group protection applies to Ma Jiaqi when the last two results lacked Cheng Ru members."""
        return (
            prize.associated_drawer == MA_JIAQI
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [user for user in self._users if user.name not in self._winner_names]
        if prize.associated_drawer == LI_BIN:
            # Special rule: only previous winners are filtered out.
            return available
        if self.is_fallback_active(prize):
            # Fallback: forcibly limit to Cheng Ru group members, even if avoided.
            return [user for user in available if user.department == CHENG_RU_GROUP]
        return [user for user in available if user.department not in prize.avoid_groups]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the current eligible pool."""
        return self._get_eligible_pool(prize)

    def count_eligible(self, prize: Prize) -> int:
        return len(self._get_eligible_pool(prize))

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        return winner

    def end_round(self, prize: Prize, winners: list[User]) -> None:
        """Record the outcome of a finished round for fallback tracking."""
        if prize.associated_drawer in (CHEN_QIXIAN, JIN_DUO) and winners:
            has_cheng_ru = any(user.department == CHENG_RU_GROUP for user in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
