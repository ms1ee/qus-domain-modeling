import random

CHENG_RU = "cheng ru"
PRE_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _is_cheng_ru(dept):
    return CHENG_RU in dept.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = set()
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winners]
        drawer = getattr(prize, "associated_drawer", None)
        if drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if _is_cheng_ru(u.department)]
        if drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def rule_description(self, prize):
        parts = ["Exclude previous winners"]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            parts.append("Li Bin: relaxed filtering (avoidance groups ignored)")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if drawer == PROTECTED_DRAWER:
            parts.append("Cheng Ru protection may apply")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.add(u.name)
        return u

    def finish_round(self, prize, winners):
        """Record fallback state after a round."""
        if prize.associated_drawer in PRE_DRAWERS:
            self.last_two_draw_results.append(any(_is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
