import random

CHEN = "Chen Qixian"
JIN = "Jin Duo"
MA = "Ma Jiaqi"
LI_BIN = "Li Bin"
CHENG_RU = "cheng ru"


def _is_cheng_ru(user):
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def _unwon(self):
        won = {w.name for w in self.winners}
        return [u for u in self.users if u.name not in won]

    def _get_eligible_pool(self, prize):
        pool = self._unwon()
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            return pool
        if (drawer == MA and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:])):
            return [u for u in pool if _is_cheng_ru(u)]
        avoid = set(prize.avoid_groups or [])
        return [u for u in pool if u.department not in avoid]

    def describe_rules(self, prize):
        d = prize.associated_drawer
        parts = ["Exclude previous winners"]
        if d == LI_BIN:
            parts = ["Exclude previous winners only (avoidance groups ignored)"]
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if d == MA:
            parts.append("fallback: if the last two draws (Chen Qixian, Jin Duo) had no "
                         "Cheng Ru group winner, pool limited to Cheng Ru group")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        return user

    def finish_round(self, prize, round_winners):
        if prize.associated_drawer in (CHEN, JIN):
            self.last_two_draw_results.append(any(_is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
