import random

LI_BIN = "Li Bin"
MONITORED = ("Chen Qixian", "Jin Duo")
TARGET = "Ma Jiaqi"
PROTECTED_GROUP = "cheng ru group"


class LotteryManager:
    def __init__(self, users):
        self.users = users
        self.winners = []
        self.last_two_draw_results = []

    def _is_won(self, u):
        return u.has_won or u in self.winners

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if not self._is_won(u)]
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            return pool
        if (drawer == TARGET and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if u.department.lower() == PROTECTED_GROUP]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winners.append(u)
        return u

    def draw_round(self, prize, control=None, on_win=None):
        """control(i) may return 'terminate' to stop the round."""
        results = []
        for i in range(1, prize.quantity + 1):
            if control and control(i) == "terminate":
                break
            u = self.draw_one(prize)
            if u is None:
                break
            results.append(u)
            if on_win:
                on_win(u)
        self.finish_round(prize, results)
        return results

    def finish_round(self, prize, results):
        if prize.associated_drawer in MONITORED:
            has = any(u.department.lower() == PROTECTED_GROUP for u in results)
            self.last_two_draw_results.append(has)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
