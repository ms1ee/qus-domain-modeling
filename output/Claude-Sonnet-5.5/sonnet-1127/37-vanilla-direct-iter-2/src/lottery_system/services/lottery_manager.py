import random

from lottery_system.services.list_manager import CHENG_RU

LI_BIN = "Li Bin"
GUARD_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


def _is_cr(dept):
    return str(dept).strip().casefold() == CHENG_RU.casefold()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []  # list of User
        self.last_two_draw_results = []

    def _winner_names(self):
        return {w.name for w in self.winners}

    def _get_eligible_pool(self, prize):
        won = self._winner_names()
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cr(u.department)]
        avoid = {g.casefold() for g in prize.avoid_groups}
        return [u for u in pool if u.department.casefold() not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_prize(self, prize, drawn):
        if prize.associated_drawer in GUARD_DRAWERS:
            self.last_two_draw_results.append(any(_is_cr(u.department) for u in drawn))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
