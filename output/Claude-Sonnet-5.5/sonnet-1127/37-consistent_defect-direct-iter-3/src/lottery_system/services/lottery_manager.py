import random

CHENG_RU_GROUP = "Cheng Ru Group"
SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


def _is_cheng_ru(dept):
    return dept.strip().lower() in ("cheng ru group", "cheng ru")


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _won_names(self):
        return {u.name for u in self.winners}

    def _fallback_active(self, prize):
        r = self.last_two_draw_results
        return (prize.associated_drawer == PROTECTED_DRAWER
                and len(r) >= 2 and not r[-1] and not r[-2])

    def _get_eligible_pool(self, prize):
        won = self._won_names()
        pool = [u for u in self.users if u.name not in won]
        if self._fallback_active(prize):
            return [u for u in pool if _is_cheng_ru(u.department)]
        if prize.associated_drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool and not self._fallback_active(prize) \
                and prize.associated_drawer != SPECIAL_DRAWER:
            # avoidance-group members are drawn after the others
            won = self._won_names()
            pool = [u for u in self.users if u.name not in won]
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def finish_round(self, prize, winners):
        """Record whether a watched drawer's round contained Cheng Ru members."""
        if prize.associated_drawer in WATCHED_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
