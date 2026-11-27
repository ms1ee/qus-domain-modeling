"""Lottery rule engine and draw execution."""

from __future__ import annotations

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
PROTECTED_GROUP = "Cheng Ru Group"
TRIGGER_DRAWERS = ["Chen Qixian", "Jin Duo"]
TARGET_DRAWER = "Ma Jiaqi"


def _norm_name(name) -> str:
    return " ".join(str(name or "").split()).lower()


def _norm_group(group) -> str:
    g = _norm_name(group)
    if g.endswith(" group"):
        g = g[: -len(" group")].strip()
    return g


def is_protected_group(department) -> bool:
    return _norm_group(department) == _norm_group(PROTECTED_GROUP)


class LotteryManager:
    """Applies lottery rules and draws winners."""

    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()
        self.fallback_applied = False

    # ------------------------------------------------------------ rule engine
    def _fallback_active(self, prize: Prize) -> bool:
        return (
            _norm_name(prize.associated_drawer) == _norm_name(TARGET_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names and not u.has_won]
        self.fallback_applied = False
        if self._fallback_active(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                self.fallback_applied = True
                return protected
        if _norm_name(prize.associated_drawer) == _norm_name(SPECIAL_DRAWER):
            return base
        avoid = {_norm_group(g) for g in prize.avoid_groups}
        if not avoid:
            return base
        return [u for u in base if _norm_group(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        desc = prize.rule_description
        if self._fallback_active(prize):
            desc += f"; FALLBACK: pool limited to {PROTECTED_GROUP} members"
        return desc

    # ---------------------------------------------------------------- drawing
    def mark_winner(self, user: User) -> None:
        self.winner_names.add(user.name)
        user.has_won = True

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self.rng.choice(pool)
        self.mark_winner(winner)
        return winner

    def record_round_result(self, prize: Prize, winners: List[User]) -> None:
        drawer = _norm_name(prize.associated_drawer)
        if drawer in {_norm_name(t) for t in TRIGGER_DRAWERS}:
            contains = any(is_protected_group(w.department) for w in winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []

    def run_round(
        self,
        prize: Prize,
        control: Optional[Callable[[int], str]] = None,
        on_draw: Optional[Callable[[int, Optional[User]], None]] = None,
    ) -> List[User]:
        """Run a full round. control(i) returns 'draw' or 'terminate'."""
        winners: List[User] = []
        for i in range(1, prize.quantity + 1):
            if control is not None and control(i) == "terminate":
                break
            user = self.draw_one(prize)
            if on_draw:
                on_draw(i, user)
            if user is None:
                break
            winners.append(user)
        self.record_round_result(prize, winners)
        return winners
