import random

CHENG_RU = ("cheng ru group", "cheng ru")


def _is_cr(user):
    return user.department.strip().lower() in CHENG_RU


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == "Li Bin":
            return pool
        if (drawer == "Ma Jiaqi" and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cr(u)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def record_drawer_result(self, prize, round_winners):
        if prize.associated_drawer in ("Chen Qixian", "Jin Duo"):
            self.last_two_draw_results.append(any(_is_cr(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
