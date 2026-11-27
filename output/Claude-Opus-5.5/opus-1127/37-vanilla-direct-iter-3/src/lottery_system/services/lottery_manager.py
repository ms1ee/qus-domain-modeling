"""Lottery rule engine."""
import random
from typing import Iterable, List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"


def _norm(text) -> str:
    return " ".join(str(text or "").split()).casefold()


def is_cheng_ru(department) -> bool:
    d = _norm(department)
    if d.endswith(" group"):
        d = d[: -len(" group")]
    return d.replace(" ", "") == "chengru"


class LotteryManager:
    """Applies lottery rules and draws winners."""

    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self._winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ---- rule helpers ----
    @staticmethod
    def _drawer_is(prize: Prize, drawer: str) -> bool:
        return _norm(prize.associated_drawer) == _norm(drawer)

    def is_fallback_triggered(self, prize: Prize) -> bool:
        if not self._drawer_is(prize, FALLBACK_DRAWER):
            return False
        last = self.last_two_draw_results[-2:]
        return len(last) == 2 and not any(last)

    def has_won(self, user: User) -> bool:
        return user.name in self._winner_names

    def describe_rules(self, prize: Prize) -> str:
        if self.is_fallback_triggered(prize):
            return ("Fallback mechanism active: prize pool limited to 'Cheng Ru group' members "
                    "(avoidance groups ignored); previous winners excluded")
        if self._drawer_is(prize, SPECIAL_DRAWER):
            return "Special drawer Li Bin: only previous winners are excluded (no avoidance groups)"
        if prize.avoid_groups:
            return ("Previous winners excluded; avoidance groups: " + ", ".join(prize.avoid_groups))
        return "Previous winners excluded; no avoidance groups"

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if not self.has_won(u)]
        if self.is_fallback_triggered(prize):
            cheng_ru = [u for u in available if is_cheng_ru(u.department)]
            if cheng_ru:
                return cheng_ru
        if self._drawer_is(prize, SPECIAL_DRAWER):
            return available
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in available if _norm(u.department) not in avoid]

    # ---- drawing ----
    def register_winner(self, user: User) -> bool:
        if self.has_won(user):
            return False
        self._winner_names.add(user.name)
        self.winners.append(user)
        return True

    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.register_winner(user)
        return user

    def record_round_result(self, prize: Prize, round_winners: Iterable[User]) -> None:
        round_winners = list(round_winners)
        if any(self._drawer_is(prize, d) for d in MONITORED_DRAWERS):
            self.last_two_draw_results.append(any(is_cheng_ru(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._drawer_is(prize, FALLBACK_DRAWER):
            self.last_two_draw_results = []
