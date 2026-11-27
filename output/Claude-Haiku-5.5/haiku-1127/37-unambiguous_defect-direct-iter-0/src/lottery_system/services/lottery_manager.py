"""Lottery rule engine and draw execution."""

import random

from lottery_system.constants import (
    CHENG_RU_GROUP,
    FALLBACK_TRIGGER_DRAWERS,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager


def _is_drawer(prize: Prize, drawer_name: str) -> bool:
    """Return True if the prize's lottery person matches the given name."""
    if prize.associated_drawer is None:
        return False
    return prize.associated_drawer.strip().casefold() == drawer_name.casefold()


class LotteryManager:
    """Executes lottery draws while applying the lottery rule engine."""

    def __init__(self, users: list[User]):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Cheng Ru group presence (True/False) in the two most recent rounds
        # drawn by Chen Qixian or Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._rng = random.Random()

    def _winner_names(self) -> set[str]:
        return {winner.user.name for winner in self.result_manager.get_all_winners()}

    def is_fallback_active(self) -> bool:
        """True if neither of the last two trigger-drawer rounds included Cheng Ru members."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def is_fallback_for(self, prize: Prize) -> bool:
        """True if the fallback mechanism forces this prize's pool to Cheng Ru members."""
        return _is_drawer(prize, MA_JIAQI) and self.is_fallback_active()

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the candidate pool for a prize under the lottery rules.

        - Previous winners are always excluded (anti-duplication).
        - Li Bin's prizes use relaxed rules: avoidance groups are ignored.
        - Ma Jiaqi's prizes are restricted to Cheng Ru group members when the
          fallback is active (even if that group is an avoidance group).
        - Otherwise members of the prize's avoidance groups are excluded.
        """
        winners = self._winner_names()
        available = [user for user in self.users if user.name not in winners]

        if _is_drawer(prize, LI_BIN):
            return available

        if self.is_fallback_for(prize):
            protected = [user for user in available if user.in_group(CHENG_RU_GROUP)]
            if protected:
                return protected

        return [
            user
            for user in available
            if not any(user.in_group(group) for group in prize.avoid_groups)
        ]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible candidate pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.result_manager.add_winner(user, prize)
        return user

    def record_round_result(self, prize: Prize, round_winners: list[User]) -> None:
        """Record whether a finished round of a trigger drawer included Cheng Ru members."""
        if not any(_is_drawer(prize, drawer) for drawer in FALLBACK_TRIGGER_DRAWERS):
            return
        has_cheng_ru = any(user.in_group(CHENG_RU_GROUP) for user in round_winners)
        self.last_two_draw_results = (self.last_two_draw_results + [has_cheng_ru])[-2:]
