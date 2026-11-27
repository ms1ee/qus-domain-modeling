"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.default_data import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import User
from lottery_system.services.result_manager import ResultManager, Winner


def _norm(text) -> str:
    return (text or "").strip().casefold()


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Draws winners while enforcing the lottery rules."""

    def __init__(self, users, result_manager=None, rng=None) -> None:
        self.users: list[User] = list(users)
        self.result_manager: ResultManager = result_manager or ResultManager()
        self.rng = rng or random.Random()
        # Results (True = contained a Cheng Ru group member) of the two most
        # recent draws by the lottery persons Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []

    def _available_users(self) -> list[User]:
        """Users who have not won any prize yet (anti-duplication)."""
        winner_names = {
            _norm(winner.user.name) for winner in self.result_manager.get_all_winners()
        }
        return [user for user in self.users if _norm(user.name) not in winner_names]

    def _cheng_ru_protection_active(self) -> bool:
        """True when the last two Chen/Jin draws both had no Cheng Ru winner."""
        return len(self.last_two_draw_results) >= 2 and not any(
            self.last_two_draw_results[-2:]
        )

    def _get_eligible_pool(self, prize) -> list[User]:
        """Return the users who may be drawn for the given prize."""
        available = self._available_users()
        drawer = _norm(prize.associated_drawer)

        # Special rule: lottery person Li Bin gets relaxed filtering.
        if drawer == _norm(LI_BIN):
            return available

        # Fallback: Ma Jiaqi is forced into the Cheng Ru group when protection
        # is triggered, overriding the prize's avoidance groups.
        if drawer == _norm(MA_JIAQI) and self._cheng_ru_protection_active():
            forced = [user for user in available if _is_cheng_ru(user)]
            if forced:
                return forced

        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in available if _norm(user.department) not in avoid]

    def draw_one(self, prize) -> Winner | None:
        """Draw a single winner for the prize. Returns None if pool is empty."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        user = self.rng.choice(pool)
        winner = self.result_manager.add_winner(user, prize)

        drawer = _norm(prize.associated_drawer)
        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            self.last_two_draw_results.append(_is_cheng_ru(user))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner
