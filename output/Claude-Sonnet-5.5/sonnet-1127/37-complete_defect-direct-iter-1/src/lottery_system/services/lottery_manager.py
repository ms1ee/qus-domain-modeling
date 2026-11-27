import random

CHENG_RU = "cheng ru group"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _is_cheng_ru(user):
    return user.department.strip().lower() == CHENG_RU


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = set()
        self.last_two_draw_results = []

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winners]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cheng_ru(u)]
        avoid = {g.strip().lower() for g in (prize.avoid_groups or [])}
        return [u for u in pool if u.department.strip().lower() not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.add(u.name)
        return u

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in WATCHED_DRAWERS:
            self.last_two_draw_results.append(any(_is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    @staticmethod
    def describe_rules(prize):
        parts = []
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("only previous winners excluded")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        parts.append("previous winners excluded")
        return "; ".join(parts)
