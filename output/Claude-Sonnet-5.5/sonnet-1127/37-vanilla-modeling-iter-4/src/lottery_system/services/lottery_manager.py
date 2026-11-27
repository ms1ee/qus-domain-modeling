import random

PROTECTED_GROUPS = ("cheng ru group", "cheng ru")
MONITORED = ("Chen Qixian", "Jin Duo")
TARGET = "Ma Jiaqi"
SPECIAL = "Li Bin"


def is_protected(user):
    return user.department.strip().lower() in PROTECTED_GROUPS


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _unwon(self):
        return [u for u in self.users if u not in self.winners]

    def _get_eligible_pool(self, prize):
        pool = self._unwon()
        drawer = prize.associated_drawer
        if drawer == TARGET and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if is_protected(u)]
        if drawer == SPECIAL:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        w = random.choice(pool)
        self.winners.append(w)
        return w

    def end_round(self, prize, round_winners):
        if prize.associated_drawer in MONITORED:
            self.last_two_draw_results.append(
                any(is_protected(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
