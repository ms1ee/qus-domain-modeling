import random

CHENG_RU = "cheng ru group"
SPECIAL_DRAWER = "Li Bin"
PROTECTED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_TARGET = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _is_cheng_ru(self, user):
        return user.department.strip().lower() == CHENG_RU

    def _get_eligible_pool(self, prize):
        won = {id(u) for u in self.winners}
        won_names = {u.name for u in self.winners}
        pool = [u for u in self.users if id(u) not in won and u.name not in won_names]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        avoid = {g.strip().lower() for g in (prize.avoid_groups or [])}
        pool = [u for u in pool if u.department.strip().lower() not in avoid]
        if (drawer == PROTECTED_TARGET and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            won_pool = [u for u in self.users
                        if u.name not in won_names and self._is_cheng_ru(u)]
            return won_pool
        return pool

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def record_round(self, prize, round_winners):
        if prize.associated_drawer in PROTECTED_DRAWERS:
            self.last_two_draw_results.append(
                any(self._is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
