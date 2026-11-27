"""Lottery rule engine."""

from __future__ import annotations

import random
from typing import Iterable, List, Optional

from lottery_system.models import Prize, User, normalize

SPECIAL_DRAWER = "Li Bin"
FALLBACK_MONITORED = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def is_cheng_ru(department: str) -> bool:
    d = normalize(department).replace("_", " ").replace("-", " ")
    d = d.replace("group", "").replace("team", "")
    d = "".join(d.split())
    return d == "chengru"


class LotteryManager:
    """Selects winners according to the configured rules."""

    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.winners = set()
        self.winner_order: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ---------- helpers ----------
    def _has_won(self, user: User) -> bool:
        if user in self.winners:
            return True
        names = {w.name if isinstance(w, User) else str(w) for w in self.winners}
        return user.name in names

    @staticmethod
    def _drawer_is(prize: Prize, person: str) -> bool:
        return normalize(prize.associated_drawer) == normalize(person)

    def is_fallback_active(self, prize: Prize) -> bool:
        return (self._drawer_is(prize, FALLBACK_TARGET)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def get_rule_description(self, prize: Prize) -> str:
        if self.is_fallback_active(prize):
            return ("Fallback rule active: pool limited to Cheng Ru group members "
                    "(avoidance overridden); previous winners excluded")
        if self._drawer_is(prize, SPECIAL_DRAWER):
            return "Special drawer Li Bin: relaxed filtering (avoidance ignored); previous winners excluded"
        return prize.rule_description()

    # ---------- core ----------
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if not self._has_won(u)]
        if self.is_fallback_active(prize):
            protected = [u for u in candidates if is_cheng_ru(u.department)]
            if protected:
                return protected
        if self._drawer_is(prize, SPECIAL_DRAWER):
            return candidates
        return [u for u in candidates if not prize.avoids(u.department)]

    def mark_winner(self, user: User) -> None:
        self.winners.add(user)
        self.winner_order.append(user)

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.mark_winner(user)
        return user

    def finish_round(self, prize: Prize, round_winners: Iterable[User]) -> None:
        """Update fallback tracking after a round completes (or is terminated)."""
        winners = list(round_winners)
        if any(self._drawer_is(prize, p) for p in FALLBACK_MONITORED):
            self.last_two_draw_results.append(any(is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._drawer_is(prize, FALLBACK_TARGET):
            self.last_two_draw_results = []
