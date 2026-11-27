"""Lottery rule engine."""

import random
from typing import Iterable, List, Optional, Set

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(text) -> str:
    return " ".join(str(text or "").split()).lower()


class LotteryManager:
    """Selects winners while applying all lottery rules."""

    def __init__(self, users) -> None:
        self.users: List[User] = []
        seen = set()
        for u in users or []:
            if u.name not in seen:
                seen.add(u.name)
                self.users.append(u)
        self.winner_names: Set[str] = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ---- rule helpers -------------------------------------------------
    @staticmethod
    def _is_protected(user: User) -> bool:
        return _norm(user.department) == _norm(PROTECTED_GROUP)

    def is_fallback_active(self, prize: Prize) -> bool:
        return (_norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return base
        if self.is_fallback_active(prize):
            protected = [u for u in base if self._is_protected(u)]
            if protected:
                return protected
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded."]
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            parts.append(f"Special rule: drawer {SPECIAL_DRAWER} - only previous "
                         "winners are filtered, avoidance groups are NOT applied.")
        elif self.is_fallback_active(prize):
            parts.append(f"Fallback rule: previous drawers {WATCHED_DRAWERS[0]} and "
                         f"{WATCHED_DRAWERS[1]} drew no '{PROTECTED_GROUP}' members, "
                         f"prize pool is limited to '{PROTECTED_GROUP}' members.")
        elif prize.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups) + ".")
        else:
            parts.append("No avoidance groups.")
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}.")
        return " ".join(parts)

    # ---- drawing ------------------------------------------------------
    def draw_next(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        self.winners.append(user)
        return user

    def complete_round(self, prize: Prize, round_winners: Iterable[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            has_protected = any(self._is_protected(u) for u in round_winners)
            self.last_two_draw_results.append(has_protected)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            # Consecutive chain broken (or fallback consumed).
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        """Draw a whole round without interaction."""
        result: List[User] = []
        for _ in range(prize.quantity):
            u = self.draw_next(prize)
            if u is None:
                break
            result.append(u)
        self.complete_round(prize, result)
        return result

    def is_winner(self, name: str) -> bool:
        return name in self.winner_names

    def reset(self) -> None:
        self.winner_names.clear()
        self.winners.clear()
        self.last_two_draw_results = []
