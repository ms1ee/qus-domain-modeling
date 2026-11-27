"""Lottery rule engine."""

from __future__ import annotations

import random
from typing import Iterable, List, Optional

from lottery_system.models import Prize, User, normalize

SPECIAL_PERSON = "Li Bin"
PROTECTED_GROUP = "Cheng Ru group"
TRIGGER_PERSONS = ["Chen Qixian", "Jin Duo"]
TARGET_PERSON = "Ma Jiaqi"


def is_protected_group(department: str) -> bool:
    return normalize(department) in ("cheng ru group", "cheng ru")


class LotteryManager:
    """Applies the lottery rules and draws winners."""

    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.special_person_name = SPECIAL_PERSON
        self.protected_group_name = PROTECTED_GROUP
        self.trigger_person_names = list(TRIGGER_PERSONS)
        self.target_person_name = TARGET_PERSON

    # ---- winner tracking -------------------------------------------------
    def mark_winner(self, user: User) -> None:
        self.winner_names.add(user.name)

    def is_winner(self, user: User) -> bool:
        return user.name in self.winner_names

    # ---- rules -----------------------------------------------------------
    def is_fallback_active(self, prize: Prize) -> bool:
        return (
            normalize(prize.associated_drawer) == normalize(self.target_person_name)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        if normalize(prize.associated_drawer) == normalize(self.special_person_name):
            return base
        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in base if normalize(u.department) not in avoid]

    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self.mark_winner(winner)
        return winner

    def record_round_result(self, prize: Prize, winners: Iterable[User]) -> None:
        drawer = normalize(prize.associated_drawer)
        if not drawer:
            return
        if drawer in {normalize(p) for p in self.trigger_person_names}:
            contains = any(is_protected_group(u.department) for u in winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []
