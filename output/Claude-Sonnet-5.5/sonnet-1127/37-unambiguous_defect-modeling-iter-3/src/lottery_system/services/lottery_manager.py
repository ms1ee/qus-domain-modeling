import random

CHENG_RU = "cheng ru"
FIRST_DRAWERS = ("Chen Qixian", "Jin Duo")
GUARDED_DRAWER = "Ma Jiaqi"
RELAXED_DRAWER = "Li Bin"


def _is_cheng_ru(user):
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winner_names = set()
        self.last_two_draw_results = []

    def _fallback_active(self, prize):
        return (prize.associated_drawer == GUARDED_DRAWER
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            return [u for u in pool if _is_cheng_ru(u)]
        if prize.associated_drawer == RELAXED_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winner_names.add(u.name)
        return u

    def finish_round(self, prize, winners):
        d = prize.associated_drawer
        if d in FIRST_DRAWERS:
            self.last_two_draw_results.append(any(_is_cheng_ru(w) for w in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif d == GUARDED_DRAWER:
            self.last_two_draw_results = []

    def rule_description(self, prize):
        parts = []
        if prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer:
            parts.append("drawer: " + prize.associated_drawer)
        if prize.associated_drawer == RELAXED_DRAWER:
            parts.append("relaxed filtering (avoidance groups ignored)")
        if self._fallback_active(prize):
            parts.append("fallback: pool limited to Cheng Ru group")
        parts.append("previous winners excluded")
        return "; ".join(parts)
