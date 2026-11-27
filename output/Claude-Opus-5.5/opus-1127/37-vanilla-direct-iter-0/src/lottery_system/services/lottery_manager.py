"""Lottery rule engine."""

from __future__ import annotations

import random
from typing import List, Optional

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru Group"
SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def is_cheng_ru_member(user: User) -> bool:
    return "cheng ru" in _norm(user.department)


class LotteryManager:
    """Applies the lottery rules and performs the draws."""

    def __init__(self, users, result_manager=None, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager
        self.rng = rng or random.SystemRandom()
        self.winners: List[User] = []
        self.winner_names = set()
        # Whether each of the last consecutive rounds by the watched drawers
        # (Chen Qixian, Jin Duo) contained Cheng Ru group members.
        self.last_two_draw_results: List[bool] = []
        self._last_two_drawers: List[str] = []

    # ------------------------------------------------------------------ rules
    def is_fallback_triggered(self, prize: Prize) -> bool:
        if _norm(prize.associated_drawer) != _norm(FALLBACK_TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _not_won(self) -> List[User]:
        return [u for u in self.users if u.name not in self.winner_names]

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = self._not_won()
        if self.is_fallback_triggered(prize):
            pool = [u for u in candidates if is_cheng_ru_member(u)]
            if pool:
                return pool
            # No Cheng Ru member left: fall back to normal rules.
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return candidates
        avoid = {_norm(g) for g in prize.avoid_groups}
        return [u for u in candidates if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if self.is_fallback_triggered(prize):
            parts.append(
                f"FALLBACK ACTIVE: the previous two lottery persons "
                f"({', '.join(FALLBACK_WATCHED_DRAWERS)}) drew no {CHENG_RU_GROUP} member, "
                f"so the prize pool is limited to {CHENG_RU_GROUP} members "
                f"(avoidance groups ignored)"
            )
        elif _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            parts.append(f"Special lottery person {SPECIAL_DRAWER}: avoidance groups are not applied")
        elif prize.avoid_groups:
            parts.append("Avoidance groups excluded: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        return "; ".join(parts)

    # ------------------------------------------------------------------ draws
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self._register_winner(user, prize)
        return user

    def _register_winner(self, user: User, prize: Prize) -> None:
        if user.name in self.winner_names:
            raise RuntimeError(f"{user.name} has already won a prize")
        self.winners.append(user)
        self.winner_names.add(user.name)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)

    def finish_round(self, prize: Prize, results) -> None:
        """Update the fallback tracking state after a round."""
        drawer = _norm(prize.associated_drawer)
        watched = [_norm(d) for d in FALLBACK_WATCHED_DRAWERS]
        if drawer in watched:
            contains = any(is_cheng_ru_member(u) for u in results)
            self.last_two_draw_results.append(contains)
            self._last_two_drawers.append(prize.associated_drawer or "")
            self.last_two_draw_results = self.last_two_draw_results[-2:]
            self._last_two_drawers = self._last_two_drawers[-2:]
        else:
            self.last_two_draw_results = []
            self._last_two_drawers = []

    def draw_prize(self, prize: Prize) -> List[User]:
        """Draw all winners of a prize at once."""
        results: List[User] = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            results.append(user)
        self.finish_round(prize, results)
        return results
