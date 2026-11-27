import random

CHENG_RU = "Cheng Ru group"
FALLBACK_SOURCES = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET = "Ma Jiaqi"
SPECIAL = "Li Bin"


class LotteryManager:
    def __init__(self, users):
        self.users = list(users)
        self.winners = []
        self.last_two_draw_results = []

    def record_winner(self, user):
        if user not in self.winners:
            self.winners.append(user)

    def _available(self):
        names = {id(w) for w in self.winners}
        return [u for u in self.users if id(u) not in names
                and u not in self.winners]

    def _get_eligible_pool(self, prize):
        pool = self._available()
        drawer = prize.associated_drawer
        if drawer == FALLBACK_TARGET and len(self.last_two_draw_results) >= 2 \
                and not any(self.last_two_draw_results[-2:]):
            return [u for u in pool if u.department == CHENG_RU]
        if drawer == SPECIAL:
            return pool
        return [u for u in pool if u.department not in prize.avoid_groups]

    def _avoided_pool(self, prize):
        if prize.associated_drawer == SPECIAL:
            return []
        return [u for u in self._available()
                if u.department in prize.avoid_groups]

    def draw_for_prize(self, prize, on_draw=None, control=None):
        """Draw winners; yields list of users. control() may return
        'pause'/'continue'/'terminate'."""
        drawn = []
        main = self._get_eligible_pool(prize)
        fallback_active = (prize.associated_drawer == FALLBACK_TARGET
                           and len(self.last_two_draw_results) >= 2
                           and not any(self.last_two_draw_results[-2:]))
        random.shuffle(main)
        extra = [] if fallback_active else self._avoided_pool(prize)
        random.shuffle(extra)
        queue = main + extra
        for i in range(prize.quantity):
            if control:
                if control() == "terminate":
                    break
            if not queue:
                break
            u = queue.pop(0)
            self.record_winner(u)
            drawn.append(u)
            if on_draw:
                on_draw(i + 1, u)
        if prize.associated_drawer in FALLBACK_SOURCES:
            self.last_two_draw_results.append(
                any(u.department == CHENG_RU for u in drawn))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return drawn
