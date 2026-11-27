import random

CHENG_RU = "cheng ru"


def _is_cheng_ru(user):
    return CHENG_RU in user.department.lower()


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winner_names = set()
        self.last_two_draw_results = []

    def _available(self):
        return [u for u in self.users
                if not getattr(u, "has_won", False) and u.name not in self.winner_names]

    def _get_eligible_pool(self, prize):
        avail = self._available()
        drawer = prize.associated_drawer
        if drawer == "Ma Jiaqi" and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in avail if _is_cheng_ru(u)]
        if drawer == "Li Bin":
            return avail
        avoid = {g.lower() for g in prize.avoid_groups}
        return [u for u in avail if u.department.lower() not in avoid]

    def describe_rules(self, prize):
        parts = ["exclude previous winners"]
        if prize.associated_drawer == "Li Bin":
            parts = ["relaxed rules (avoidance groups ignored)"]
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer:
            parts.append(f"drawer: {prize.associated_drawer}")
        return "; ".join(parts)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        u = random.choice(pool)
        u.has_won = True
        self.winner_names.add(u.name)
        return u

    def finish_round(self, prize, winners):
        if prize.associated_drawer in ("Chen Qixian", "Jin Duo"):
            self.last_two_draw_results.append(any(_is_cheng_ru(u) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def draw_round(self, prize, result_manager, control=None, on_win=None):
        """control(i) may return 'terminate' to end the round."""
        won = []
        for i in range(1, prize.quantity + 1):
            if control and control(i) == "terminate":
                break
            if on_win:
                on_win(i, None)
            u = self.draw_one(prize)
            if u is None:
                break
            result_manager.add_winner(u, prize)
            won.append(u)
            if on_win:
                on_win(i, u)
        self.finish_round(prize, won)
        return won
