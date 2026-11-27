import random

FALLBACK_GROUP = "Cheng Ru group"
SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winner_names = set()
        self.last_two_draw_results = []

    def _fallback_active(self, prize):
        return (prize.associated_drawer == FALLBACK_DRAWER
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            return [u for u in pool if u.department == FALLBACK_GROUP]
        if prize.associated_drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def rule_description(self, prize):
        parts = []
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Special drawer: only previous winners excluded")
        elif prize.avoid_groups:
            parts.append("Avoid groups (drawn last): " + ", ".join(prize.avoid_groups))
        else:
            parts.append("Previous winners excluded")
        if self._fallback_active(prize):
            parts.append(f"Fallback: pool limited to {FALLBACK_GROUP}")
        return "; ".join(parts)

    def draw_next(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool and not self._fallback_active(prize):
            # avoidance group members are drawn after other members
            pool = [u for u in self.users if u.name not in self.winner_names]
        if not pool:
            return None
        user = random.choice(pool)
        self.winner_names.add(user.name)
        return user

    def finish_round(self, prize, winners):
        drawer = prize.associated_drawer
        if drawer in WATCHED_DRAWERS:
            has = any(u.department == FALLBACK_GROUP for u in winners)
            self.last_two_draw_results.append(has)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == FALLBACK_DRAWER:
            self.last_two_draw_results = []
