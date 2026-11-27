"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm(text: Optional[str]) -> str:
    return " ".join((text or "").lower().split())


def is_protected_group(department: str) -> bool:
    d = _norm(department)
    return d in ("cheng ru group", "cheng ru")


class LotteryManager:
    """Applies filtering rules and performs draws."""

    def __init__(self, users: List[User]) -> None:
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self._winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = random.SystemRandom()

    # ------------------------------------------------------------------ #
    def _is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def _fallback_active(self, prize: Prize) -> bool:
        return (_norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if not self._is_winner(u)]
        if self._fallback_active(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return base
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        rules = ["Previous winners are excluded"]
        if self._fallback_active(prize):
            rules.append(f"Fallback mechanism active: pool limited to "
                         f"'{PROTECTED_GROUP}' members (avoidance ignored)")
        elif _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            rules.append(f"Special drawer {SPECIAL_DRAWER}: avoidance groups not applied")
        elif prize.avoid_groups:
            rules.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("No avoidance groups")
        if prize.associated_drawer:
            rules.insert(0, f"Drawer: {prize.associated_drawer}")
        return "; ".join(rules)

    def draw_one(self, prize: Prize, pool: Optional[List[User]] = None) -> Optional[User]:
        if pool is None:
            pool = self._get_eligible_pool(prize)
        pool = [u for u in pool if not self._is_winner(u)]
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winners.append(user)
        self._winner_names.add(user.name)
        return user

    def record_round_result(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            self.last_two_draw_results.append(
                any(is_protected_group(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_DRAWER):
            self.last_two_draw_results = []
