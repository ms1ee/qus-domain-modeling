import random

PROTECTED = "cheng ru"
FALLBACK_BEFORE = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET = "Ma Jiaqi"
SPECIAL = "Li Bin"


def _is_cr(user):
    return PROTECTED in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _fallback_active(self, prize):
        return (prize.associated_drawer == FALLBACK_TARGET
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize):
        won = {id(u) for u in self.winners} | {u.name for u in self.winners}
        pool = [u for u in self.users if u not in self.winners and u.name not in won]
        if self._fallback_active(prize):
            return [u for u in pool if _is_cr(u)]
        if prize.associated_drawer == SPECIAL:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def _secondary_pool(self, prize):
        """Avoided-group members: still eligible but drawn last."""
        if prize.associated_drawer == SPECIAL or self._fallback_active(prize):
            return []
        avoid = set(prize.avoid_groups or [])
        return [u for u in self.users if u.department in avoid
                and u not in self.winners]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._secondary_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.append(u)
        return u

    def finish_round(self, prize, round_winners):
        d = prize.associated_drawer
        if d in FALLBACK_BEFORE:
            self.last_two_draw_results.append(any(_is_cr(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif d == FALLBACK_TARGET:
            self.last_two_draw_results = []

    def rule_description(self, prize):
        parts = []
        if prize.associated_drawer == SPECIAL:
            parts.append("Special: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if self._fallback_active(prize):
            parts.append("Fallback: pool limited to Cheng Ru group")
        parts.append("Previous winners excluded")
        return "; ".join(parts)
