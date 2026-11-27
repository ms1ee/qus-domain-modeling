import random

PROTECTED_GROUP = "Cheng Ru group"
CHECK_PERSONS = ("Chen Qixian", "Jin Duo")
FALLBACK_PERSON = "Ma Jiaqi"
SPECIAL_PERSON = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winner_names = set()
        self.last_two_draw_results = []

    def _fallback_active(self, prize):
        return (
            prize.associated_drawer == FALLBACK_PERSON
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            return [u for u in pool if u.department == PROTECTED_GROUP]
        if prize.associated_drawer == SPECIAL_PERSON:
            return pool
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def describe_rules(self, prize):
        parts = ["Exclude previous winners"]
        if prize.associated_drawer == SPECIAL_PERSON:
            parts.append("avoidance groups ignored (Li Bin)")
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if self._fallback_active(prize):
            parts.append(f"restricted to {PROTECTED_GROUP} (fallback)")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winner_names.add(u.name)
        return u

    def finish_round(self, prize, winners):
        """Record whether a checked drawer's round included protected group members."""
        if prize.associated_drawer in CHECK_PERSONS:
            has = any(w.department == PROTECTED_GROUP for w in winners)
            self.last_two_draw_results.append(has)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
