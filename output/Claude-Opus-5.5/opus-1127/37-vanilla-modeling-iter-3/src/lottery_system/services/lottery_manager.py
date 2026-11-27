"""Lottery rule engine and draw execution."""

import random
from typing import List, Optional

from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
TARGET_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(s) -> str:
    return " ".join(str(s or "").strip().lower().split())


def is_protected_group(dept) -> bool:
    d = _norm(dept)
    return d in ("cheng ru group", "cheng ru")


class LotteryManager:
    def __init__(self, users, result_manager: Optional[ResultManager] = None, rng=None):
        self.users = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = set(w.user.name for w in self.result_manager.winners)
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.SystemRandom()

    # ---- rule helpers ----
    def is_winner(self, user) -> bool:
        return user.name in self.winner_names

    @staticmethod
    def _drawer_is(prize, name) -> bool:
        return _norm(getattr(prize, "associated_drawer", None)) == _norm(name)

    def is_fallback_active(self, prize) -> bool:
        if not self._drawer_is(prize, TARGET_DRAWER):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not self.last_two_draw_results[-1] and not self.last_two_draw_results[-2]

    def _get_eligible_pool(self, prize):
        not_won = [u for u in self.users if not self.is_winner(u)]
        if self.is_fallback_active(prize):
            protected = [u for u in not_won if is_protected_group(u.department)]
            if protected:
                return protected
        if self._drawer_is(prize, SPECIAL_DRAWER):
            return not_won
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in not_won if _norm(u.department) not in avoid]

    def describe_rules(self, prize) -> str:
        desc = prize.rule_description()
        if self._drawer_is(prize, SPECIAL_DRAWER):
            desc += f"; Special rule: drawn by {SPECIAL_DRAWER}, avoidance groups NOT applied"
        if self.is_fallback_active(prize):
            desc += (f"; Fallback active: pool limited to '{PROTECTED_GROUP}' members "
                     f"(previous rounds by {', '.join(TRIGGER_DRAWERS)} had none)")
        return desc

    # ---- drawing ----
    def record_winner(self, user, prize):
        if self.is_winner(user):
            raise ValueError(f"{user.name} has already won")
        self.winner_names.add(user.name)
        return self.result_manager.add_winner(user, prize)

    def draw_one(self, prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.record_winner(user, prize)
        return user

    def finish_round(self, prize, round_winners):
        drawer = _norm(getattr(prize, "associated_drawer", None))
        if drawer in {_norm(n) for n in TRIGGER_DRAWERS}:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []

    def remaining_quantity(self, prize) -> int:
        drawn = sum(1 for w in self.result_manager.winners if w.prize_name == prize.name)
        return max(0, prize.quantity - drawn)
