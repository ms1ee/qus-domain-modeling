"""Lottery rule engine and draw execution."""

from __future__ import annotations

import random
from typing import List, Optional

from lottery_system.models import Prize, User

SPECIAL_PERSON = "li bin"
MONITORED_PERSONS = ("chen qixian", "jin duo")
TARGET_PERSON = "ma jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def is_protected_group(department) -> bool:
    key = _norm(department).replace(" ", "")
    if key.endswith("group"):
        key = key[: -len("group")]
    return key == "chengru"


class LotteryManager:
    """Applies the rule engine and draws winners."""

    def __init__(self, users, result_manager=None, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager
        self.winners: List[User] = []
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ------------------------------------------------------------ rule engine
    def _fallback_triggered(self) -> bool:
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results[-2:])

    def _already_won(self, user) -> bool:
        if user.name in self.winner_names:
            return True
        if self.result_manager is not None and self.result_manager.has_won(user):
            return True
        return False

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if not self._already_won(u)]
        drawer = _norm(prize.associated_drawer)

        if drawer == TARGET_PERSON and self._fallback_triggered():
            protected = [u for u in available if is_protected_group(u.department)]
            if protected:
                return protected

        if drawer == SPECIAL_PERSON:
            return available

        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        if not avoid:
            return available
        preferred = [u for u in available if _norm(u.department) not in avoid]
        if preferred:
            return preferred
        # Avoidance group members are only drawn after all other members.
        return available

    def is_fallback_active(self, prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == TARGET_PERSON and self._fallback_triggered()

    # ---------------------------------------------------------------- drawing
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winners.append(user)
        self.winner_names.add(user.name)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, round_winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in MONITORED_PERSONS:
            hit = any(is_protected_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == TARGET_PERSON:
            self.last_two_draw_results = []

    def draw_round(self, prize: Prize) -> List[User]:
        result = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            result.append(user)
        self.finish_round(prize, result)
        return result
