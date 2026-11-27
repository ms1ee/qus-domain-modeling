import random

CHENG_RU = "Cheng Ru group"
TRACKED = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
SPECIAL = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _base(self, prize):
        won = {w.name for w in self.winners}
        return [u for u in self.users if u.name not in won]

    def _get_eligible_pool(self, prize):
        pool = self._base(prize)
        drawer = prize.associated_drawer
        if (drawer == FALLBACK_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            cr = [u for u in pool if u.department == CHENG_RU]
            if cr:
                return cr
        if drawer == SPECIAL:
            return pool
        return [u for u in pool if u.department not in prize.avoid_groups]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = [u for u in self._base(prize)]
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        if prize.associated_drawer in TRACKED:
            self.last_two_draw_results.append(user.department == CHENG_RU)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return user
