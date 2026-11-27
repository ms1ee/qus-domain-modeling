"""Lottery rule engine and drawing logic."""

from __future__ import annotations

import random
from typing import List, Optional, Set

from lottery_system.models import Prize, User

SPECIAL_PERSON = "Li Bin"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(text: Optional[str]) -> str:
    return " ".join((text or "").strip().lower().split())


def is_protected_group(department: str) -> bool:
    d = _norm(department).replace("_", " ").replace("-", " ")
    d = " ".join(d.split())
    if d.endswith(" group"):
        d = d[: -len(" group")].strip()
    return d in ("cheng ru", "chengru")


class LotteryManager:
    """Applies rules and performs draws."""

    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users or [])
        self.rng = rng or random.Random()
        self.winner_names: Set[str] = set()
        self.last_two_draw_results: List[bool] = []
        self.fallback_used_last = False

    # ------------------------------------------------------------- rule checks
    @staticmethod
    def is_special_drawer(prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == _norm(SPECIAL_PERSON)

    def is_fallback_triggered(self, prize: Prize) -> bool:
        if _norm(prize.associated_drawer) != _norm(FALLBACK_TARGET):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results[-2:])

    def get_rule_description(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if self.is_fallback_triggered(prize):
            parts.append(
                f"FALLBACK: pool limited to '{PROTECTED_GROUP}' members "
                f"(previous two draws by {' and '.join(MONITORED_DRAWERS)} had no such winners)"
            )
        elif self.is_special_drawer(prize):
            parts.append(f"Special drawer {SPECIAL_PERSON}: avoidance groups are NOT applied")
        elif prize.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        if prize.associated_drawer:
            parts.append(f"Drawer: {prize.associated_drawer}")
        return "; ".join(parts)

    # ------------------------------------------------------------------- pools
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_triggered(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        if self.is_special_drawer(prize):
            return base
        avoid = {_norm(g) for g in prize.avoid_groups}
        return [u for u in base if _norm(u.department) not in avoid]

    # ------------------------------------------------------------------- draws
    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self.rng.choice(pool)
        self.winner_names.add(winner.name)
        return winner

    def draw_round(self, prize: Prize) -> List[User]:
        winners = []
        for _ in range(prize.quantity):
            w = self.draw_winner(prize)
            if w is None:
                break
            winners.append(w)
        self.record_round_result(prize, winners)
        return winners

    def record_round_result(self, prize: Prize, round_winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in MONITORED_DRAWERS}:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_TARGET):
            self.fallback_used_last = not any(self.last_two_draw_results[-2:]) and len(
                self.last_two_draw_results
            ) >= 2
            self.last_two_draw_results = []
        else:
            self.last_two_draw_results = []
