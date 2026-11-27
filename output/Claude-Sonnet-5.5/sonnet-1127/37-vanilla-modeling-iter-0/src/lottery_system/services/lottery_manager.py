import random

CHENG_RU = "cheng ru group"
SPECIAL_DRAWER = "Li Bin"
CHECKED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _has_won(self, u):
        return u.has_won or any(w is u or w.name == u.name for w in self.winners)

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if not self._has_won(u)]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if u.department.lower() == CHENG_RU]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winners.append(u)
        return u

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in CHECKED_DRAWERS:
            has = any(w.department.lower() == CHENG_RU for w in round_winners)
            self.last_two_draw_results.append(has)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
