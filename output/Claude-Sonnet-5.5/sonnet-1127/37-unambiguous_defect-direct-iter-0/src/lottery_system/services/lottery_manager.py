import random

CHENG_RU_KEY = "cheng ru"
FALLBACK_SOURCES = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET = "Ma Jiaqi"
RELAXED_DRAWER = "Li Bin"


def is_cheng_ru(user):
    return CHENG_RU_KEY in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {id(u) for u in self.winners}
        won_names = {u.name for u in self.winners}
        pool = [u for u in self.users if id(u) not in won and u.name not in won_names]
        drawer = prize.associated_drawer
        if (drawer == FALLBACK_TARGET and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if is_cheng_ru(u)]
        if drawer == RELAXED_DRAWER:
            return pool
        avoid = {g.strip().lower() for g in prize.avoid_groups}
        return [u for u in pool if u.department.strip().lower() not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in FALLBACK_SOURCES:
            self.last_two_draw_results.append(any(is_cheng_ru(u) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
