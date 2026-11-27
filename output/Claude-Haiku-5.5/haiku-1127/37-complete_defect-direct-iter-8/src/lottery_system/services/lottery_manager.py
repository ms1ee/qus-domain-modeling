"""Lottery execution and rule engine."""

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons whose round results feed the Cheng Ru protection check.
TRACKED_DRAWERS = (CHEN_QIXIAN, JIN_DUO)


def _norm(text) -> str:
    return " ".join(str(text).strip().split()).lower()


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


def _user_key(user: User) -> str:
    return _norm(user.name)


class LotteryManager:
    """Runs lottery rounds while applying the lottery rule engine."""

    def __init__(self, users, rng=None):
        self._users: list[User] = list(users)
        self._rng = rng if rng is not None else random.Random()
        self._winner_keys: set[str] = set()
        self.winners: list[User] = []
        self.result_manager = ResultManager()
        # Round results (True = the round contained Cheng Ru group members)
        # for the last two rounds drawn by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._round_prize: Prize | None = None
        self._round_winners: list[User] = []

    # ----- rule helpers -------------------------------------------------

    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)

    def fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection: if neither of the last two Chen/Jin rounds had
        Cheng Ru members, Ma Jiaqi's prize pool is limited to Cheng Ru members."""
        return (
            self._is_drawer(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def is_winner(self, user: User) -> bool:
        return _user_key(user) in self._winner_keys

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        # Anti-duplication: previous winners are always excluded.
        pool = [user for user in self._users if not self.is_winner(user)]

        # Special rule: Li Bin only filters previous winners.
        if self._is_drawer(prize, LI_BIN):
            return pool

        # Fallback (Cheng Ru protection) overrides avoidance groups.
        if self.fallback_active(prize):
            return [user for user in pool if _is_cheng_ru(user)]

        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in pool if _norm(user.department) not in avoid]

    # ----- round control -----------------------------------------------

    def start_round(self, prize: Prize) -> None:
        self._round_prize = prize
        self._round_winners = []

    def draw_next(self) -> User | None:
        """Draw one winner for the current round. Returns None if no one is eligible."""
        if self._round_prize is None:
            raise RuntimeError("No lottery round in progress. Call start_round() first.")
        pool = self._get_eligible_pool(self._round_prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_keys.add(_user_key(user))
        self.winners.append(user)
        self._round_winners.append(user)
        self.result_manager.add_winner(user, self._round_prize)
        return user

    def finish_round(self) -> list[User]:
        """Close the current round, update fallback history and return its winners."""
        prize = self._round_prize
        if prize is None:
            return []
        if any(self._is_drawer(prize, drawer) for drawer in TRACKED_DRAWERS):
            had_cheng_ru = any(_is_cheng_ru(user) for user in self._round_winners)
            self.last_two_draw_results.append(had_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        result = list(self._round_winners)
        self._round_prize = None
        self._round_winners = []
        return result

    @property
    def round_winners(self) -> list[User]:
        return list(self._round_winners)
