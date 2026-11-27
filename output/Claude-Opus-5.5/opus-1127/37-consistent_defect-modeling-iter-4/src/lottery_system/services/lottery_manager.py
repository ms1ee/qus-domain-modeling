"""Lottery rule engine and draw execution."""

import random
from typing import Iterable, List, Optional

from lottery_system.models import Prize, User

SPECIAL_PERSON = "Li Bin"
FALLBACK_TRIGGER_PERSONS = ["Chen Qixian", "Jin Duo"]
FALLBACK_TARGET_PERSON = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _norm_person(name) -> str:
    return " ".join((name or "").strip().lower().split())


def _norm_group(name) -> str:
    return (name or "").strip().lower()


def _is_protected_group(dept) -> bool:
    key = "".join((dept or "").lower().split())
    if key.endswith("group"):
        key = key[:-5]
    return key == "chengru"


class LotteryManager:
    """Applies the rule engine and draws winners."""

    def __init__(self, users, existing_winners: Optional[Iterable[User]] = None):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self.rng = random.Random()
        for u in existing_winners or []:
            self.mark_winner(u)

    # ---- rule helpers ----
    def _not_won(self) -> List[User]:
        return [u for u in self.users if u.name not in self.winner_names]

    def is_special_person(self, drawer) -> bool:
        return _norm_person(drawer) == _norm_person(SPECIAL_PERSON)

    def is_fallback_active(self, prize: Prize) -> bool:
        if _norm_person(prize.associated_drawer) != _norm_person(FALLBACK_TARGET_PERSON):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _avoided(self, user: User, prize: Prize) -> bool:
        groups = {_norm_group(g) for g in (prize.avoid_groups or [])}
        return _norm_group(user.department) in groups

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = self._not_won()
        if self.is_fallback_active(prize):
            protected = [u for u in candidates if _is_protected_group(u.department)]
            if protected:
                return protected
        if self.is_special_person(prize.associated_drawer):
            return candidates
        return [u for u in candidates if not self._avoided(u, prize)]

    def _get_deferred_pool(self, prize: Prize) -> List[User]:
        """Avoidance-group members: still eligible but drawn after others."""
        return [u for u in self._not_won() if self._avoided(u, prize)]

    def describe_rules(self, prize: Prize) -> str:
        rules = ["Previous winners are excluded"]
        if self.is_fallback_active(prize):
            rules.append(f"Fallback active: pool limited to '{PROTECTED_GROUP}' members "
                         f"(avoidance groups ignored)")
        elif self.is_special_person(prize.associated_drawer):
            rules.append(f"Special lottery person {SPECIAL_PERSON}: avoidance groups not applied")
        elif prize.avoid_groups:
            rules.append("Avoidance groups (drawn only after other members): "
                         + ", ".join(prize.avoid_groups))
        else:
            rules.append("No avoidance groups")
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        return "; ".join(rules)

    # ---- draw ----
    def mark_winner(self, user: User):
        if user.name not in self.winner_names:
            self.winner_names.add(user.name)
            self.winners.append(user)

    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool and not self.is_special_person(prize.associated_drawer):
            pool = self._get_deferred_pool(prize)
        pool = [u for u in pool if u.name not in self.winner_names]
        if not pool:
            return None
        winner = self.rng.choice(pool)
        self.mark_winner(winner)
        return winner

    def finish_round(self, prize: Prize, round_winners: List[User]):
        drawer = _norm_person(prize.associated_drawer)
        if drawer in {_norm_person(p) for p in FALLBACK_TRIGGER_PERSONS}:
            has_protected = any(_is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(has_protected)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm_person(FALLBACK_TARGET_PERSON):
            self.last_two_draw_results = []
