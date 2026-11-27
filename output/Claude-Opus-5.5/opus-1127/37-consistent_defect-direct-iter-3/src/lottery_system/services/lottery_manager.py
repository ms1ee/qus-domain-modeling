"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCHED = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"


def is_cheng_ru(department: str) -> bool:
    return "cheng ru" in (department or "").lower()


class LotteryManager:
    """Applies filtering rules and draws winners."""

    def __init__(self, users, result_manager=None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []

    # ---------- rules ----------
    def _is_winner(self, user: User) -> bool:
        if user.name in self.winner_names:
            return True
        if self.result_manager is not None and self.result_manager.has_won(user):
            return True
        return False

    def _is_forced(self, prize: Prize) -> bool:
        return (
            prize.associated_drawer == FALLBACK_DRAWER
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _normal_pool(self, prize: Prize) -> List[User]:
        avoid = set(prize.avoid_groups or [])
        apply_avoid = prize.associated_drawer != SPECIAL_DRAWER
        return [
            u for u in self.users
            if not self._is_winner(u) and not (apply_avoid and u.department in avoid)
        ]

    def _get_eligible_pool(self, prize) -> List[User]:
        if self._is_forced(prize):
            return [u for u in self.users if not self._is_winner(u) and is_cheng_ru(u.department)]
        return self._normal_pool(prize)

    def _candidate_pool(self, prize: Prize) -> List[User]:
        pool = self._get_eligible_pool(prize)
        if pool:
            return pool
        if self._is_forced(prize):
            pool = self._normal_pool(prize)
            if pool:
                return pool
        # Avoided groups remain eligible but are drawn after the others.
        return [u for u in self.users if not self._is_winner(u)]

    def rule_description(self, prize: Prize) -> str:
        parts = []
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Special rule: only previous winners are excluded (avoidance groups ignored)")
        else:
            parts.append("Previous winners excluded")
            if prize.avoid_groups:
                parts.append("Avoidance groups (drawn last): " + ", ".join(prize.avoid_groups))
        if self._is_forced(prize):
            parts.append("Fallback active: pool limited to Cheng Ru group members")
        return "; ".join(parts)

    # ---------- drawing ----------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._candidate_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winner_names.add(user.name)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, winners: List[User]) -> None:
        drawer = prize.associated_drawer
        if drawer in FALLBACK_WATCHED:
            self.last_two_draw_results.append(any(is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == FALLBACK_DRAWER:
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        winners = []
        for _ in range(prize.quantity):
            u = self.draw_one(prize)
            if u is None:
                break
            winners.append(u)
        self.finish_round(prize, winners)
        return winners
