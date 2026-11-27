import random

CHENG_RU = "cheng ru"


def is_cheng_ru(user):
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if (drawer == "Ma Jiaqi" and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if is_cheng_ru(u)]
        if drawer == "Li Bin":
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def record_round_result(self, round_winners):
        self.last_two_draw_results.append(any(is_cheng_ru(u) for u in round_winners))
        self.last_two_draw_results = self.last_two_draw_results[-2:]

    @staticmethod
    def describe_rules(prize):
        parts = []
        if prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer == "Li Bin":
            parts.append("relaxed filtering (Li Bin)")
        if prize.associated_drawer == "Ma Jiaqi":
            parts.append("Cheng Ru group protection may apply")
        parts.append("previous winners excluded")
        return "; ".join(parts)
