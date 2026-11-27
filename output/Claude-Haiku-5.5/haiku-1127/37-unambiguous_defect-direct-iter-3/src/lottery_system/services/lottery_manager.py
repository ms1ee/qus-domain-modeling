"""Lottery rule engine: eligibility filtering, drawing and fallback protection."""

from __future__ import annotations

import random

from lottery_system.config import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Results of the last two rounds run by Chen Qixian / Jin Duo.
        # True means that round produced at least one Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        self._rng = random.Random()

    # ----- winner tracking -------------------------------------------------
    def mark_winner(self, user: User) -> None:
        self._winner_names.add(user.name)

    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def remaining_users(self) -> list[User]:
        """Users who have not won any prize yet."""
        return [user for user in self._users if user.name not in self._winner_names]

    # ----- rule engine -----------------------------------------------------
    def is_cheng_ru_protection_active(self, prize: Prize) -> bool:
        """Fallback: Ma Jiaqi's round is restricted to Cheng Ru group members when
        neither of the last two Chen Qixian / Jin Duo rounds had a Cheng Ru winner."""
        return (
            prize.associated_drawer == MA_JIAQI
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        candidates = self.remaining_users()

        # Fallback mechanism overrides all other rules, including avoidance groups.
        if self.is_cheng_ru_protection_active(prize):
            return [user for user in candidates if user.department == CHENG_RU_GROUP]

        # Special rule: Li Bin's rounds use relaxed filtering (avoidance groups ignored).
        if prize.associated_drawer == LI_BIN:
            return candidates

        # Basic filtering: exclude avoidance groups.
        avoid = set(prize.avoid_groups)
        return [user for user in candidates if user.department not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the current eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for ``prize``. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.mark_winner(user)
        return user

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback state after a round has ended."""
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            hit = any(user.department == CHENG_RU_GROUP for user in round_winners)
            self.last_two_draw_results.append(hit)
            del self.last_two_draw_results[:-2]
        elif drawer == MA_JIAQI:
            # A Ma Jiaqi round starts a new cycle of observation.
            self.last_two_draw_results.clear()
