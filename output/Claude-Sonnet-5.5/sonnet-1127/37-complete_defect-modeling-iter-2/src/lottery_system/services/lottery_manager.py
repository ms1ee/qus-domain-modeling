import random

PROTECTED_GROUP = "Cheng Ru Group"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
TARGET_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _is_protected(self, dept):
        return dept.strip().lower() == PROTECTED_GROUP.lower()

    def _fallback_active(self, prize):
        return (prize.associated_drawer == TARGET_DRAWER
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize):
        won = {w.name for w in self.winners}
        pool = [u for u in self.users if u.name not in won]
        if self._fallback_active(prize):
            return [u for u in pool if self._is_protected(u.department)]
        if prize.associated_drawer == SPECIAL_DRAWER:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def describe_rules(self, prize):
        parts = ["Exclude previous winners"]
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Special drawer: avoidance groups ignored")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if self._fallback_active(prize):
            parts.append(f"Fallback: pool limited to {PROTECTED_GROUP}")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winners.append(u)
        return u

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in MONITORED_DRAWERS:
            self.last_two_draw_results.append(
                any(self._is_protected(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
