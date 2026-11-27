"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "li bin"
WATCHED_DRAWERS = ("chen qixian", "jin duo")
PROTECTED_DRAWER = "ma jiaqi"
PROTECTED_GROUP = "cheng ru group"


def _norm(s) -> str:
    return (s or "").strip().lower()


def is_protected_member(user: User) -> bool:
    return _norm(user.department) == PROTECTED_GROUP


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []

    def _available(self) -> List[User]:
        return [u for u in self.users if u.name not in self.winner_names]

    def is_fallback_active(self, prize: Prize) -> bool:
        return (_norm(prize.associated_drawer) == PROTECTED_DRAWER
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = self._available()
        if self.is_fallback_active(prize):
            return [u for u in available if is_protected_member(u)]
        if _norm(prize.associated_drawer) == SPECIAL_DRAWER:
            return available
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in available if _norm(u.department) not in avoid]

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.mark_winner(user)
        return user

    def mark_winner(self, user: User) -> bool:
        if user.name in self.winner_names:
            return False
        self.winner_names.add(user.name)
        self.winners.append(user)
        return True

    def finish_round(self, prize: Prize, round_winners) -> None:
        if _norm(prize.associated_drawer) in WATCHED_DRAWERS:
            contains = any(is_protected_member(u) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
