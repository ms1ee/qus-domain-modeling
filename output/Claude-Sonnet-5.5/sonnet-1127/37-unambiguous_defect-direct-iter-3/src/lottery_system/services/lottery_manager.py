import random
from typing import List, Optional

from lottery_system.models import Prize, User

CHENG_RU = "cheng ru"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
RELAXED_DRAWER = "Li Bin"


def _is_cheng_ru(user: User) -> bool:
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        won = set(self.winners)
        pool = [u for u in self.users if u not in won]
        drawer = prize.associated_drawer
        if drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if _is_cheng_ru(u)]
        if drawer == RELAXED_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def finish_prize(self, prize: Prize, round_winners) -> None:
        if prize.associated_drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
