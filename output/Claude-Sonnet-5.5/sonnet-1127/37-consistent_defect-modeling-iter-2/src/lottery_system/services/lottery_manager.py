import random

CHENG_RU = "cheng ru"


def _is_cheng_ru(user):
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        won = {w.name for w in self.winners}
        pool = [u for u in self.users if u.name not in won]
        drawer = prize.associated_drawer
        if drawer == "Ma Jiaqi" and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if _is_cheng_ru(u)]
        if drawer == "Li Bin":
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def _avoided_members(self, prize):
        won = {w.name for w in self.winners}
        avoid = set(prize.avoid_groups or [])
        return [u for u in self.users
                if u.name not in won and u.department in avoid]

    def rule_description(self, prize):
        parts = []
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        if prize.associated_drawer == "Li Bin":
            parts.append("Avoidance rules not applied")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer == "Ma Jiaqi" and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            parts.append("Cheng Ru group protection active")
        parts.append("Previous winners excluded")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool and prize.associated_drawer != "Li Bin":
            fallback_active = (prize.associated_drawer == "Ma Jiaqi"
                               and len(self.last_two_draw_results) >= 2
                               and not any(self.last_two_draw_results[-2:]))
            if not fallback_active:
                pool = self._avoided_members(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def record_round(self, prize, round_winners):
        if prize.associated_drawer in ("Chen Qixian", "Jin Duo"):
            self.last_two_draw_results.append(
                any(_is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
