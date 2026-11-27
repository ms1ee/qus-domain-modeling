import random

SPECIAL_DRAWER = "Li Bin"
FALLBACK_GROUP = "cheng ru"
MONITORED = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"


def _is_cheng_ru(dept):
    return FALLBACK_GROUP in dept.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = set()
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winners and not u.has_won]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        normal = [u for u in pool if u.department not in avoid]
        if (drawer == FALLBACK_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            forced = [u for u in pool if _is_cheng_ru(u.department)]
            if forced:
                return forced
        return normal

    def draw(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winners.add(u.name)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in MONITORED:
            self.last_two_draw_results.append(
                any(_is_cheng_ru(w.department) for w in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
