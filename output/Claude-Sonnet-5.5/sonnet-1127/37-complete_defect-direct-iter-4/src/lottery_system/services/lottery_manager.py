import random

CHENG_RU_KEY = "chengru"
FIRST_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _is_cheng_ru(dept):
    return CHENG_RU_KEY in dept.lower().replace(" ", "")


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []  # list of User
        self.last_two_draw_results = []

    def _is_winner(self, user):
        return any(w is user or w.name == user.name for w in self.winners)

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if not self._is_winner(u)]
        drawer = prize.associated_drawer
        if drawer == SPECIAL_DRAWER:
            return pool
        if (drawer == PROTECTED_DRAWER and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cheng_ru(u.department)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def record_round(self, prize, round_winners):
        if prize.associated_drawer in FIRST_DRAWERS:
            self.last_two_draw_results.append(
                any(_is_cheng_ru(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def rule_description(self, prize):
        parts = ["exclude previous winners"]
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("avoid-group rules not applied (special drawer)")
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer == PROTECTED_DRAWER:
            parts.append("Cheng Ru group protection may apply")
        return "; ".join(parts)
