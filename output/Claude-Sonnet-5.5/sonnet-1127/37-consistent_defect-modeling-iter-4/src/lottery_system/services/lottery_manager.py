import random

CHENG_RU_GROUPS = {"Cheng Ru group", "Cheng Ru", "Cheng Ru Group"}
TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
TARGET_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _winner_names(self):
        return {u.name for u in self.winners}

    def _get_eligible_pool(self, prize):
        won = self._winner_names()
        base = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return base
        if (drawer == TARGET_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            pool = [u for u in base if u.department in CHENG_RU_GROUPS]
            if pool:
                return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in base if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def record_round(self, prize, round_winners):
        if prize.associated_drawer in TRIGGER_DRAWERS:
            has = any(u.department in CHENG_RU_GROUPS for u in round_winners)
            self.last_two_draw_results.append(has)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def describe_rules(self, prize):
        parts = []
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Only previous winners excluded; avoidance groups not applied")
        else:
            parts.append("Previous winners excluded")
            if prize.avoid_groups:
                parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer == TARGET_DRAWER:
            parts.append("fallback: Cheng Ru group protection may apply")
        return "; ".join(parts)
