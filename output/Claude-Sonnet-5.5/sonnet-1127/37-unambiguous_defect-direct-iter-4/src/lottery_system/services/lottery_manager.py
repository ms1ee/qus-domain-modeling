import random

CHENG_RU_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
RELAXED_DRAWER = "Li Bin"


def is_cheng_ru(department):
    d = str(department).lower().replace(" ", "")
    return d.startswith("chengru") or "程如" in d


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == RELAXED_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if is_cheng_ru(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def record_round_result(self, prize, winners):
        if prize.associated_drawer in CHENG_RU_DRAWERS:
            self.last_two_draw_results.append(
                any(is_cheng_ru(w.department) for w in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
