"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCH_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


class LotteryManager:
    """Executes draws according to the rule engine."""

    def __init__(self, users, result_manager=None, rng=None) -> None:
        self.users: List[User] = list(users)
        self.result_manager = result_manager
        self.rng = rng or random.Random()
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self.current_round_winners: List[User] = []

    # ----------------------------------------------------------------- rules
    def _is_winner(self, user: User) -> bool:
        return user.name in self.winner_names

    def is_fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def describe_rules(self, prize: Prize) -> str:
        desc = prize.rule_description()
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            desc += "; Special rule: relaxed filtering (avoidance groups ignored)"
        if self.is_fallback_active(prize):
            desc += (
                f"; Fallback active: pool limited to '{PROTECTED_GROUP}' members"
            )
        return desc

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if not self._is_winner(u)]
        if self.is_fallback_active(prize):
            return [u for u in candidates if _norm(u.department) == _norm(PROTECTED_GROUP)]
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return candidates
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in candidates if _norm(u.department) not in avoid]

    # ----------------------------------------------------------------- draws
    def start_round(self, prize: Prize) -> None:
        self.current_round_winners = []

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winner_names.add(user.name)
        self.winners.append(user)
        self.current_round_winners.append(user)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize) -> List[User]:
        drawer = _norm(prize.associated_drawer)
        results = list(self.current_round_winners)
        if drawer in {_norm(d) for d in FALLBACK_WATCH_DRAWERS}:
            contains = any(_norm(u.department) == _norm(PROTECTED_GROUP) for u in results)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_DRAWER):
            self.last_two_draw_results = []
        self.current_round_winners = []
        return results

    def run_round(self, prize: Prize) -> List[User]:
        """Draw a whole round without interaction."""
        self.start_round(prize)
        for _ in range(prize.quantity):
            if self.draw_one(prize) is None:
                break
        return self.finish_round(prize)
