"""Lottery rule engine and drawing logic."""

from __future__ import annotations

import random
from typing import List, Optional

from lottery_system.models import Prize, User, normalize_group

SPECIAL_PERSON = "Li Bin"
FALLBACK_TRIGGER_PERSONS = ["Chen Qixian", "Jin Duo"]
FALLBACK_TARGET_PERSON = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm_person(name) -> str:
    return normalize_group(name)


def is_protected_group(department: str) -> bool:
    d = normalize_group(department)
    return d in ("cheng ru group", "cheng ru")


class LotteryManager:
    """Applies rules and draws winners."""

    def __init__(self, users, result_manager=None, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager
        self.winners: List[User] = []
        self._winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()
        self.special_person_name = SPECIAL_PERSON

    # ------------------------------------------------------------- helpers
    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def is_fallback_active(self, prize: Prize) -> bool:
        if _norm_person(prize.associated_drawer) != _norm_person(FALLBACK_TARGET_PERSON):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results[-2:])

    def describe_rules(self, prize: Prize) -> str:
        if _norm_person(prize.associated_drawer) == _norm_person(SPECIAL_PERSON):
            return (f"Special lottery person {SPECIAL_PERSON}: only previous winners are "
                    f"excluded, avoidance groups are NOT applied")
        if self.is_fallback_active(prize):
            return (f"Fallback triggered: pool limited to '{PROTECTED_GROUP}' members "
                    f"(previous winners excluded, avoidance groups ignored)")
        return prize.rule_description()

    # -------------------------------------------------------------- engine
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if not self.is_winner(u)]
        drawer = _norm_person(prize.associated_drawer)
        if drawer == _norm_person(SPECIAL_PERSON):
            return candidates
        if self.is_fallback_active(prize):
            return [u for u in candidates if is_protected_group(u.department)]
        avoid = {normalize_group(g) for g in prize.avoid_groups}
        return [u for u in candidates if normalize_group(u.department) not in avoid]

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.record_winner(user, prize)
        return user

    def record_winner(self, user: User, prize: Prize) -> bool:
        if self.is_winner(user):
            return False
        self._winner_names.add(user.name)
        self.winners.append(user)
        user.has_won = True
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return True

    def complete_round(self, prize: Prize, round_winners: List[User]) -> None:
        """Update fallback tracking after a round finishes."""
        drawer = _norm_person(prize.associated_drawer)
        triggers = {_norm_person(p) for p in FALLBACK_TRIGGER_PERSONS}
        if drawer in triggers:
            contains = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm_person(FALLBACK_TARGET_PERSON):
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        """Non-interactive full round draw."""
        result = []
        for _ in range(prize.quantity):
            u = self.draw_one(prize)
            if u is None:
                break
            result.append(u)
        self.complete_round(prize, result)
        return result
