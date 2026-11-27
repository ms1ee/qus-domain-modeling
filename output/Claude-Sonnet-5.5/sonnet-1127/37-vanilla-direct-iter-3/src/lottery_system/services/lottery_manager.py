import random

PROTECTED_GROUP = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
TRACKED_DRAWERS = ("Chen Qixian", "Jin Duo")
GUARDED_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _winner_names(self):
        return {u.name for u in self.winners}

    def _get_eligible_pool(self, prize):
        won = self._winner_names()
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == GUARDED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if u.department == PROTECTED_GROUP]
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
        if prize.associated_drawer in TRACKED_DRAWERS:
            self.last_two_draw_results.append(
                any(u.department == PROTECTED_GROUP for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
