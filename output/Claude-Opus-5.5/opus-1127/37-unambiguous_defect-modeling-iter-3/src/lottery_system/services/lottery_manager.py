"""Lottery rule engine and draw execution."""
from __future__ import annotations

import random
from typing import List, Optional

from lottery_system.models import Prize, User


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _norm_group(text) -> str:
    t = _norm(text)
    if t.endswith(" group"):
        t = t[: -len(" group")].strip()
    return t


class LotteryManager:
    RELAXED_DRAWER = "Li Bin"
    TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
    TARGET_DRAWER = "Ma Jiaqi"
    PROTECTED_GROUP = "Cheng Ru"

    def __init__(self, users, rng: Optional[random.Random] = None) -> None:
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # --------------------------------------------------------------- helpers
    def is_protected_member(self, user: User) -> bool:
        return _norm_group(user.department) == _norm_group(self.PROTECTED_GROUP)

    def is_relaxed(self, prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == _norm(self.RELAXED_DRAWER)

    def is_fallback_triggered(self, prize: Prize) -> bool:
        if _norm(prize.associated_drawer) != _norm(self.TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def has_won(self, user: User) -> bool:
        return user.name in self.winner_names

    # --------------------------------------------------------------- engine
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        not_won = [u for u in self.users if not self.has_won(u)]
        if self.is_fallback_triggered(prize):
            protected = [u for u in not_won if self.is_protected_member(u)]
            if protected:
                return protected
        if self.is_relaxed(prize):
            return not_won
        avoid = {_norm_group(g) for g in (prize.avoid_groups or [])}
        return [u for u in not_won if _norm_group(u.department) not in avoid]

    def get_rule_description(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if self.is_fallback_triggered(prize):
            parts.append(f"Fallback triggered: pool limited to '{self.PROTECTED_GROUP}' group "
                         "members (avoidance ignored)")
        elif self.is_relaxed(prize):
            parts.append(f"Relaxed rule for drawer {self.RELAXED_DRAWER}: avoidance groups ignored")
        elif prize.avoid_groups:
            parts.append("Avoiding groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        return "; ".join(parts)

    def mark_winner(self, user: User) -> bool:
        if self.has_won(user):
            return False
        self.winners.append(user)
        self.winner_names.add(user.name)
        return True

    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.mark_winner(user)
        return user

    def draw_round(self, prize: Prize) -> List[User]:
        result = []
        for _ in range(prize.quantity):
            u = self.draw_winner(prize)
            if u is None:
                break
            result.append(u)
        self.finish_round(prize, result)
        return result

    def finish_round(self, prize: Prize, round_winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in self.TRIGGER_DRAWERS}:
            self.last_two_draw_results.append(
                any(self.is_protected_member(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(self.TARGET_DRAWER):
            self.last_two_draw_results = []
