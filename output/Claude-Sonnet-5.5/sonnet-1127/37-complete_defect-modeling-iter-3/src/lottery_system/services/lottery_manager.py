import random

CHEN = "Chen Qixian"
JIN = "Jin Duo"
MA = "Ma Jiaqi"
SPECIAL = "Li Bin"


def is_cheng_ru(dept):
    return "cheng ru" in dept.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == MA and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if is_cheng_ru(u.department)]
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

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in (CHEN, JIN):
            self.last_two_draw_results.append(
                any(is_cheng_ru(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
