"""Lottery rule engine: eligibility filtering and winner drawing."""

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize_text,
    same_text,
)


class LotteryManager:
    """Runs draws while enforcing the lottery rules.

    Rules implemented:
    - Previous winners are always excluded (anti-duplication).
    - Prizes with a lottery person exclude that prize's avoidance groups,
      except for the special "Li Bin" rule which only excludes winners.
    - Cheng Ru Group protection: if the last two draws of Chen Qixian / Jin Duo
      contained no Cheng Ru Group member, Ma Jiaqi's prize pool is limited to
      Cheng Ru Group members (ignoring avoidance groups).
    """

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_keys: set[str] = set()
        # Records, for the most recent draws by Chen Qixian / Jin Duo, whether
        # the round contained a Cheng Ru Group member. Keeps at most two entries.
        self.last_two_draw_results: list[bool] = []
        self._random = random.Random()

    def is_winner(self, user: User) -> bool:
        """Return True if the user has already won a prize."""
        return normalize_text(user.name) in self._winner_keys

    def _is_cheng_ru(self, user: User) -> bool:
        return same_text(user.department, CHENG_RU_GROUP)

    def is_cheng_ru_fallback_active(self) -> bool:
        """Return True when the Cheng Ru Group protection is triggered."""
        return (
            len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may win the given prize right now."""
        available = [user for user in self.users if not self.is_winner(user)]
        drawer = prize.associated_drawer

        if drawer and same_text(drawer, MA_JIAQI) and self.is_cheng_ru_fallback_active():
            return [user for user in available if self._is_cheng_ru(user)]

        if drawer and same_text(drawer, LI_BIN):
            return available

        return [
            user
            for user in available
            if not any(same_text(user.department, group) for group in prize.avoid_groups)
        ]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._random.choice(pool)
        self._winner_keys.add(normalize_text(winner.name))
        self.winners.append(winner)
        return winner

    def record_round_result(self, prize: Prize, round_winners: list[User]) -> None:
        """Update the Cheng Ru Group protection state after a prize round."""
        drawer = prize.associated_drawer
        if drawer and (same_text(drawer, CHEN_QIXIAN) or same_text(drawer, JIN_DUO)):
            contains_cheng_ru = any(self._is_cheng_ru(user) for user in round_winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
