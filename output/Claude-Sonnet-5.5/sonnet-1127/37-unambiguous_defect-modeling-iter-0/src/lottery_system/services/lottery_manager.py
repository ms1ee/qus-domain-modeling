import random

CHENG_RU = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA = "Ma Jiaqi"
TRACKED = ("Chen Qixian", "Jin Duo")


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = set()
        self.last_two_draw_results = []

    def _is_cheng_ru(self, user):
        return user.department.strip().lower() == CHENG_RU.lower()

    def _get_eligible_pool(self, prize):
        pool = [u for u in self.users
                if u not in self.winners and u.name not in {w.name for w in self.winners}]
        drawer = prize.associated_drawer
        if drawer == MA and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if self._is_cheng_ru(u)]
        if drawer == LI_BIN:
            return pool  # relaxed: avoidance groups ignored
        avoid = {g.strip().lower() for g in prize.avoid_groups}
        return [u for u in pool if u.department.strip().lower() not in avoid]

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        self.winners.add(u)
        u.has_won = True
        return u

    def record_round(self, prize, round_winners):
        """Track whether tracked drawers' results contained Cheng Ru members."""
        if prize.associated_drawer in TRACKED:
            self.last_two_draw_results.append(
                any(self._is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
