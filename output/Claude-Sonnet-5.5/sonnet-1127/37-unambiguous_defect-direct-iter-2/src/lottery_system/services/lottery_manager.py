import random

CHENG_RU = "Cheng Ru"
SPECIAL_DRAWER = "Li Bin"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if u.department == CHENG_RU]
        if drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(
                any(u.department == CHENG_RU for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
