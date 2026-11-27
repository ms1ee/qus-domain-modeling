"""Lottery rule engine: eligibility filtering, special rules, fallback and anti-duplication."""

from __future__ import annotations

import random

from lottery_system.constants import (
    CHENG_RU_GROUP,
    FALLBACK_DRAWER,
    FALLBACK_TRIGGER_DRAWERS,
    SPECIAL_DRAWER,
)
from lottery_system.models import Prize, User


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


def is_cheng_ru_member(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Performs draws while enforcing all lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.winners: list[User] = []
        # Per-round results of lottery persons Chen Qixian / Jin Duo:
        # True when that round produced a Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    def is_winner(self, user: User) -> bool:
        return _norm(user.name) in self._winner_keys

    def _is_drawer(self, prize: Prize, drawer_name: str) -> bool:
        return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)

    def is_fallback_active(self, prize: Prize) -> bool:
        """Fallback applies to Ma Jiaqi when the last two Chen/Jin results both lack Cheng Ru members."""
        if not self._is_drawer(prize, FALLBACK_DRAWER):
            return False
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        candidates = [user for user in self._users if not self.is_winner(user)]

        # Special rule: Li Bin only filters previous winners.
        if self._is_drawer(prize, SPECIAL_DRAWER):
            return candidates

        # Fallback rule: forced to Cheng Ru group members, overriding avoidance groups.
        if self.is_fallback_active(prize):
            return [user for user in candidates if is_cheng_ru_member(user)]

        # Basic rule: exclude winners and avoidance groups.
        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in candidates if _norm(user.department) not in avoid]

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(_norm(winner.name))
        self.winners.append(winner)
        return winner

    def record_round_result(self, prize: Prize, round_winners: list[User]) -> None:
        """Record whether a round drawn by Chen Qixian or Jin Duo hit the Cheng Ru group."""
        if prize.associated_drawer is None:
            return
        if any(self._is_drawer(prize, trigger) for trigger in FALLBACK_TRIGGER_DRAWERS):
            hit = any(is_cheng_ru_member(user) for user in round_winners)
            self.last_two_draw_results.append(hit)
            del self.last_two_draw_results[:-2]

    def describe_rule(self, prize: Prize) -> str:
        parts: list[str] = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}.")
        if self._is_drawer(prize, SPECIAL_DRAWER):
            parts.append("Special rule: only previous winners are excluded; avoidance groups do not apply.")
        elif self.is_fallback_active(prize):
            parts.append(
                f"Fallback rule: neither of the last two rounds by {' / '.join(FALLBACK_TRIGGER_DRAWERS)} "
                f"hit {CHENG_RU_GROUP}, so only {CHENG_RU_GROUP} members are eligible "
                "(avoidance groups overridden)."
            )
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                parts.append("Avoided groups: " + ", ".join(prize.avoid_groups) + ".")
            else:
                parts.append("No avoidance groups.")
        return " ".join(parts)
