import random
from typing import List, Optional

from ..models import Prize, User

CHENG_RU_GROUP = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


def _is_cheng_ru(user: User) -> bool:
    return user.department.strip().lower() == CHENG_RU_GROUP.lower()


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []

    def _is_winner(self, user: User) -> bool:
        return any(w.name == user.name for w in self.winners)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        pool = [u for u in self.users if not self._is_winner(u)]
        drawer = prize.associated_drawer
        if drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if _is_cheng_ru(u)]
        if drawer != SPECIAL_DRAWER and prize.avoid_groups:
            pool = [u for u in pool if u.department not in prize.avoid_groups]
        return pool

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def finish_round(self, prize: Prize, round_winners: List[User]) -> None:
        """Update fallback tracking after a round completes."""
        if prize.associated_drawer in WATCHED_DRAWERS:
            self.last_two_draw_results.append(any(_is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
