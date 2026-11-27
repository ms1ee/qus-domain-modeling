"""Lottery rule engine and draw execution."""

from __future__ import annotations

import random
from typing import Iterable, List, Optional

from lottery_system.models import Prize, User


def _norm(s) -> str:
    return " ".join(str(s or "").strip().lower().split())


class LotteryManager:
    RELAXED_DRAWER = "Li Bin"
    TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
    FALLBACK_DRAWER = "Ma Jiaqi"
    PROTECTED_GROUP = "Cheng Ru group"

    def __init__(self, users, rng=None):
        self.users: List[User] = list(users or [])
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self._rng = rng or random.SystemRandom()

    # ----------------------------------------------------------------- helpers
    @classmethod
    def is_protected_member(cls, user: User) -> bool:
        dep = _norm(user.department)
        target = _norm(cls.PROTECTED_GROUP)
        return dep == target or "cheng ru" in dep

    def _drawer_is(self, prize: Prize, person: str) -> bool:
        return _norm(prize.associated_drawer) == _norm(person)

    def is_relaxed(self, prize: Prize) -> bool:
        return self._drawer_is(prize, self.RELAXED_DRAWER)

    def is_fallback_active(self, prize: Prize) -> bool:
        if not self._drawer_is(prize, self.FALLBACK_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) >= 2 and not any(recent)

    def is_winner(self, user: User) -> bool:
        return user.name in self.winner_names

    # ------------------------------------------------------------- rule engine
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if not self.is_winner(u)]
        if self.is_fallback_active(prize):
            protected = [u for u in available if self.is_protected_member(u)]
            if protected:
                return protected
        if self.is_relaxed(prize):
            return available
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in available if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if self.is_fallback_active(prize):
            parts.append(f"FALLBACK ACTIVE: pool limited to '{self.PROTECTED_GROUP}' members "
                         f"(Cheng Ru group protection)")
        elif self.is_relaxed(prize):
            parts.append(f"Relaxed rules for lottery person {self.RELAXED_DRAWER}: "
                         f"avoidance groups are ignored")
        elif prize.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        return "; ".join(parts)

    # ------------------------------------------------------------------ drawing
    def mark_winner(self, user: User) -> bool:
        if self.is_winner(user):
            return False
        self.winner_names.add(user.name)
        return True

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.mark_winner(user)
        return user

    def record_round_result(self, prize: Prize, winners: Iterable[User]) -> None:
        winners = list(winners)
        if any(self._drawer_is(prize, p) for p in self.TRIGGER_DRAWERS):
            self.last_two_draw_results.append(any(self.is_protected_member(u) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._drawer_is(prize, self.FALLBACK_DRAWER):
            self.last_two_draw_results = []

    def reset(self) -> None:
        self.winner_names.clear()
        self.last_two_draw_results = []
