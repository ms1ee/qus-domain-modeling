"""Lottery rule engine and drawing logic."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_PERSON = "Li Bin"
PROTECTED_GROUP = "Cheng Ru group"
TRIGGER_PERSONS = ("Chen Qixian", "Jin Duo")
TARGET_PERSON = "Ma Jiaqi"


def _norm(s: Optional[str]) -> str:
    return " ".join((s or "").strip().lower().split())


def is_protected_group(department: str) -> bool:
    return "cheng ru" in _norm(department)


class LotteryManager:
    """Applies lottery rules and draws winners."""

    def __init__(self, users) -> None:
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []

    # ---- rule engine -------------------------------------------------
    def _fallback_active(self, prize: Prize) -> bool:
        return (_norm(prize.associated_drawer) == _norm(TARGET_PERSON)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        if _norm(prize.associated_drawer) == _norm(SPECIAL_PERSON):
            return base
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if self._fallback_active(prize):
            parts.append(f"Fallback active: pool limited to '{PROTECTED_GROUP}' members")
        elif _norm(drawer) == _norm(SPECIAL_PERSON):
            parts.append(f"Special drawer {SPECIAL_PERSON}: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if drawer:
            parts.append(f"Drawer: {drawer}")
        return "; ".join(parts)

    # ---- drawing -----------------------------------------------------
    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self.mark_winner(winner)
        return winner

    def mark_winner(self, user: User) -> None:
        if user.name not in self.winner_names:
            self.winner_names.add(user.name)
            self.winners.append(user)

    def record_round_result(self, prize: Prize, round_winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(p) for p in TRIGGER_PERSONS}:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(TARGET_PERSON):
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        """Non-interactive round draw."""
        result: List[User] = []
        for _ in range(prize.quantity):
            w = self.draw_winner(prize)
            if w is None:
                break
            result.append(w)
        self.record_round_result(prize, result)
        return result
