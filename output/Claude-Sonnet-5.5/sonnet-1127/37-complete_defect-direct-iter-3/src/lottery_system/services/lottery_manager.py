import random

PROTECTED_GROUP = "Cheng Ru group"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self._winner_names = set()
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self._winner_names]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (
            drawer == FALLBACK_DRAWER
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        ):
            return [u for u in pool if u.department == PROTECTED_GROUP]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        self._winner_names.add(u.name)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in WATCHED_DRAWERS:
            self.last_two_draw_results.append(
                any(w.department == PROTECTED_GROUP for w in winners)
            )
            self.last_two_draw_results = self.last_two_draw_results[-2:]
