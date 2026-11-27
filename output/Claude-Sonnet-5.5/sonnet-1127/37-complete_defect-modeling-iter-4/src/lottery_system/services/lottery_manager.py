import random

SPECIAL_DRAWER = "Li Bin"
MONITORED = ("Chen Qixian", "Jin Duo")
TARGET = "Ma Jiaqi"
PROTECTED = "cheng ru"


def _is_protected(user):
    return PROTECTED in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _available(self):
        return [u for u in self.users if not u.has_won and u not in self.winners]

    def _get_eligible_pool(self, prize):
        pool = self._available()
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == TARGET and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_protected(u)]
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

    def finish_round(self, prize, round_winners):
        drawer = prize.associated_drawer
        if drawer in MONITORED:
            self.last_two_draw_results.append(
                any(_is_protected(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == TARGET:
            self.last_two_draw_results = []

    def rule_description(self, prize):
        parts = []
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Avoidance rules ignored")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        parts.append("Previous winners excluded")
        return "; ".join(parts)
