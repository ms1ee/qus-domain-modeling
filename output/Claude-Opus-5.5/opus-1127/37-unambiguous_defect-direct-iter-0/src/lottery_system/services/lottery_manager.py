"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import (
    FALLBACK_TARGET_DRAWER,
    FALLBACK_WATCHED_DRAWERS,
    SPECIAL_DRAWER_RELAXED,
    Prize,
    User,
    is_cheng_ru_group,
    normalize,
)


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[User] = []
        # Results (contains Cheng Ru group member?) of the most recent
        # draws by the watched drawers (Chen Qixian, Jin Duo); max 2 items.
        self.last_two_draw_results: List[bool] = []
        self.rng = random.Random()

    # ---------- rule helpers ----------
    def _is_winner(self, user: User) -> bool:
        return user.name.lower() in self.winner_names

    def _fallback_active(self, prize: Prize) -> bool:
        if normalize(prize.associated_drawer) != normalize(FALLBACK_TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if not self._is_winner(u)]
        if self._fallback_active(prize):
            pool = [u for u in available if is_cheng_ru_group(u.department)]
            if pool:
                return pool
        if normalize(prize.associated_drawer) == normalize(SPECIAL_DRAWER_RELAXED):
            return available
        avoid = {normalize(g) for g in (prize.avoid_groups or [])}
        return [u for u in available if normalize(u.department) not in avoid]

    def is_fallback_active(self, prize: Prize) -> bool:
        return self._fallback_active(prize)

    # ---------- drawing ----------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winner_names.add(user.name.lower())
        self.winners.append(user)
        return user

    def record_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = normalize(prize.associated_drawer)
        watched = {normalize(d) for d in FALLBACK_WATCHED_DRAWERS}
        if drawer in watched:
            contains = any(is_cheng_ru_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == normalize(FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []
