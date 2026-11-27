import random
from typing import List

from lottery_system.models import User, Prize

PROTECTED_GROUP = "cheng ru"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _is_protected(dept: str) -> bool:
    return PROTECTED_GROUP in dept.lower()


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        won = {w.name for w in self.winners}
        pool = [u for u in self.users if not u.has_won and u.name not in won]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if drawer == FALLBACK_DRAWER and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if _is_protected(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def rule_description(self, prize: Prize) -> str:
        parts = ["Exclude previous winners"]
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts = ["Exclude previous winners only (avoidance groups ignored for Li Bin)"]
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer == FALLBACK_DRAWER:
            parts.append("fallback: Cheng Ru group protection may apply")
        return "; ".join(parts)

    def draw_one(self, prize: Prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winners.append(u)
        return u

    def finish_round(self, prize: Prize, winners: List[User]) -> None:
        if prize.associated_drawer in WATCHED_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_protected(w.department) for w in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
