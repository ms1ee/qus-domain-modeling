import random

CHECK_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _is_cr(dept):
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
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cr(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in CHECK_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_cr(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    @staticmethod
    def describe(prize):
        d = f"Quantity: {prize.quantity}"
        d += f", Avoid groups: {', '.join(prize.avoid_groups) or 'None'}"
        if prize.associated_drawer:
            d += f", Drawer: {prize.associated_drawer}"
            if prize.associated_drawer == SPECIAL_DRAWER:
                d += " (only previous winners excluded)"
        return d
