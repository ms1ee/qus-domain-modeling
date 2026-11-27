import random


def _is_cheng_ru(dept):
    return "cheng ru" in dept.lower()


class LotteryManager:
    SPECIAL_DRAWER = "Li Bin"
    MONITORED = ("Chen Qixian", "Jin Duo")
    PROTECTED_DRAWER = "Ma Jiaqi"

    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {u.name for u in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == self.SPECIAL_DRAWER:
            return pool
        if (drawer == self.PROTECTED_DRAWER
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cheng_ru(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in self.MONITORED:
            self.last_two_draw_results.append(
                any(_is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def rule_description(self, prize):
        if prize.associated_drawer == self.SPECIAL_DRAWER:
            return "Only previous winners excluded; avoidance groups ignored"
        d = "Previous winners excluded"
        if prize.avoid_groups:
            d += "; avoiding groups: " + ", ".join(prize.avoid_groups)
        if prize.associated_drawer == self.PROTECTED_DRAWER:
            d += "; Cheng Ru group protection may apply"
        return d
