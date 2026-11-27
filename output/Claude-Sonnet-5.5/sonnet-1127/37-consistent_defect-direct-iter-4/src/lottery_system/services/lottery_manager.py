import random
from typing import List, Optional

from lottery_system.models import Prize, User

CHENG_RU = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        won = {w.name for w in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if u.department == CHENG_RU]
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

    def record_round(self, prize: Prize, round_winners: List[User]):
        if prize.associated_drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(
                any(u.department == CHENG_RU for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
