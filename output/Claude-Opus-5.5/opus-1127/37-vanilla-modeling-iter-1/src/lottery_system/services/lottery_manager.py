"""Lottery rule engine and draw execution."""

from __future__ import annotations

import random
from typing import List, Optional

from lottery_system.models import (
    FALLBACK_TARGET_DRAWER,
    MONITORED_DRAWERS,
    SPECIAL_DRAWER,
    Prize,
    User,
    is_cheng_ru_group,
    normalize_name,
)


class LotteryManager:
    """Applies the rule engine and performs draws."""

    def __init__(self, users, result_manager=None) -> None:
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ----- rule helpers -----
    @staticmethod
    def _is_drawer(prize: Prize, target: str) -> bool:
        return normalize_name(prize.associated_drawer) == normalize_name(target)

    def is_fallback_active(self, prize: Prize) -> bool:
        if not self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            return False
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def describe_rule(self, prize: Prize) -> str:
        if self.is_fallback_active(prize):
            return ("Fallback mechanism active (Cheng Ru group protection): "
                    "prize pool limited to Cheng Ru group members, excluding previous winners")
        if self._is_drawer(prize, SPECIAL_DRAWER):
            return (f"Special drawer {SPECIAL_DRAWER}: only previous winners are excluded, "
                    "avoidance groups not applied")
        desc = "Excludes previous winners"
        if prize.avoid_groups:
            desc += f"; avoids groups: {', '.join(prize.avoid_groups)}"
        return desc

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        not_won = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            return [u for u in not_won if is_cheng_ru_group(u.department)]
        if self._is_drawer(prize, SPECIAL_DRAWER):
            return not_won
        avoid = {normalize_name(g) for g in (prize.avoid_groups or [])}
        return [u for u in not_won if normalize_name(u.department) not in avoid]

    # ----- drawing -----
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        self.winners.append(user)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, round_winners) -> None:
        """Update fallback tracking after a round is finished."""
        drawer = normalize_name(prize.associated_drawer)
        if drawer and drawer in {normalize_name(d) for d in MONITORED_DRAWERS}:
            has_cr = any(is_cheng_ru_group(u.department) for u in round_winners)
            self.last_two_draw_results.append(has_cr)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []

    def draw(self, prize: Prize) -> List[User]:
        """Non-interactive draw of a full round."""
        result: List[User] = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            result.append(user)
        self.finish_round(prize, result)
        return result
