import random

SPECIAL_DRAWER = "Li Bin"
GUARD_DRAWERS = ("Chen Qixian", "Jin Duo")
FINAL_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "cheng ru"


def _is_protected(dept):
    return PROTECTED_GROUP in dept.casefold()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = set(self.winners)
        pool = [u for u in self.users if u not in won]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == FINAL_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_protected(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def record_round(self, prize, round_winners):
        if prize.associated_drawer in GUARD_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_protected(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
