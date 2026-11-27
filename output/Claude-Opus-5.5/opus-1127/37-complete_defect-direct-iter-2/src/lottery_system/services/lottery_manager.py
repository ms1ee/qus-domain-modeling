"""Lottery rule engine."""

import random
from typing import List, Optional, Set

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm(text) -> str:
    return " ".join(str(text or "").split()).lower()


def is_protected_group(department) -> bool:
    return _norm(department) == _norm(PROTECTED_GROUP)


class LotteryManager:
    """Applies the lottery rules and performs draws."""

    def __init__(self, users) -> None:
        self.users: List[User] = list(users)
        self.winner_names: Set[str] = set()
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ---- rules -------------------------------------------------------
    def _not_won(self) -> List[User]:
        return [u for u in self.users if u.name not in self.winner_names]

    def fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize) -> List[User]:
        base = self._not_won()
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return base
        if self.fallback_active(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        rules = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if _norm(drawer) == _norm(SPECIAL_DRAWER):
            rules.append(f"Special drawer {SPECIAL_DRAWER}: avoidance groups are NOT applied")
        elif self.fallback_active(prize):
            rules.append(
                f"Fallback triggered: pool limited to '{PROTECTED_GROUP}' members "
                "(avoidance groups ignored)"
            )
        elif prize.avoid_groups:
            rules.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("No avoidance groups")
        if drawer:
            rules.insert(0, f"Drawer: {drawer}")
        return "; ".join(rules)

    # ---- drawing -----------------------------------------------------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        return user

    def mark_winner(self, user: User) -> None:
        self.winner_names.add(user.name)

    def record_round(self, prize: Prize, winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            has_protected = any(is_protected_group(u.department) for u in winners)
            self.last_two_draw_results.append(has_protected)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []
