import random

CHENG_RU = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _available(self):
        won = {w.name for w in self.winners}
        return [u for u in self.users if u.name not in won]

    def _get_eligible_pool(self, prize):
        pool = self._available()
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if u.department == CHENG_RU]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, round_winners):
        drawer = prize.associated_drawer
        if drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(
                any(u.department == CHENG_RU for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == PROTECTED_DRAWER:
            self.last_two_draw_results = []
