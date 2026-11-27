"""Lottery rule engine."""
import random
from typing import List, Optional, Set

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(s: Optional[str]) -> str:
    return " ".join((s or "").split()).lower()


def is_protected_group(department: str) -> bool:
    return _norm(department) == _norm(PROTECTED_GROUP)


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users or [])
        self.winner_names: Set[str] = set()
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ---------- rule helpers ----------
    def is_fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def describe_rules(self, prize: Prize) -> str:
        rules = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if _norm(drawer) == _norm(SPECIAL_DRAWER):
            rules.append(f"Special drawer {SPECIAL_DRAWER}: avoidance groups are NOT applied")
        elif self.is_fallback_active(prize):
            rules.append(
                f"Fallback active: pool limited to '{PROTECTED_GROUP}' members "
                f"(avoidance groups ignored)"
            )
        elif prize.avoid_groups:
            rules.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("No avoidance groups")
        if drawer:
            rules.append(f"Drawer: {drawer}")
        return "; ".join(rules)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        drawer = _norm(prize.associated_drawer)
        if drawer == _norm(SPECIAL_DRAWER):
            return base
        if self.is_fallback_active(prize):
            return [u for u in base if is_protected_group(u.department)]
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    # ---------- drawing ----------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        return user

    def finish_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_DRAWER):
            self.last_two_draw_results = []
