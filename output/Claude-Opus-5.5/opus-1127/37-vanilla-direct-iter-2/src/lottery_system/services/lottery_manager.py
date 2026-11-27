"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
WATCH_DRAWERS = ("Chen Qixian", "Jin Duo")
TARGET_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm(text) -> str:
    return "".join(str(text or "").split()).casefold()


def is_protected_group(department) -> bool:
    d = _norm(department)
    return d in ("chengrugroup", "chengru")


class LotteryManager:
    """Applies filtering rules and performs draws."""

    def __init__(self, users, result_manager: Optional[ResultManager] = None, rng=None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = set(self.result_manager.winner_names())
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ------------------------------------------------------------- rules
    def is_fallback_active(self, prize: Prize) -> bool:
        if _norm(prize.associated_drawer) != _norm(TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            protected = [u for u in available if is_protected_group(u.department)]
            if protected:
                return protected
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return available
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in available if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if self.is_fallback_active(prize):
            parts.append(
                f"FALLBACK ACTIVE: pool limited to '{PROTECTED_GROUP}' members "
                f"(previous two drawers' results contained no {PROTECTED_GROUP} member)"
            )
        elif _norm(drawer) == _norm(SPECIAL_DRAWER):
            parts.append(f"Special drawer {SPECIAL_DRAWER}: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append("Avoidance groups excluded: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        if drawer:
            parts.append(f"Drawer: {drawer}")
        return "; ".join(parts)

    # -------------------------------------------------------------- draw
    def record_winner(self, user: User, prize: Prize) -> bool:
        if user.name in self.winner_names:
            return False
        winner = self.result_manager.add_winner(user, prize)
        self.winner_names.add(user.name)
        return winner is not None

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.record_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCH_DRAWERS}:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(TARGET_DRAWER):
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        """Non-interactive full round draw."""
        winners: List[User] = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            winners.append(user)
        self.finish_round(prize, winners)
        return winners
