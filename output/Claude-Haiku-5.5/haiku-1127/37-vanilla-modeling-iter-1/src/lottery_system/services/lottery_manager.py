"""Lottery rule engine: eligibility filtering and fair random drawing."""
from __future__ import annotations

import random

from lottery_system.models import (
    CHENG_RU_GROUP,
    FALLBACK_TARGET_DRAWER,
    FALLBACK_TRIGGER_DRAWERS,
    SPECIAL_DRAWER_LI_BIN,
    Prize,
    User,
)


def _same(a: str, b: str) -> bool:
    return a.strip().casefold() == b.strip().casefold()


def _is_cheng_ru(user: User) -> bool:
    return _same(user.department, CHENG_RU_GROUP)


def _user_key(user: User) -> str:
    return user.name.strip().casefold()


class LotteryManager:
    """Applies lottery rules and performs the draws.

    Rules:
    - Previous winners are never drawn again (anti-duplication).
    - Members of the prize's avoidance groups are excluded.
    - Special person "Li Bin": only previous winners are filtered.
    - Fallback: if the last two draws by Chen Qixian / Jin Duo contained no
      Cheng Ru Group member, Ma Jiaqi's pool is restricted to Cheng Ru Group
      members (overriding avoidance groups).
    """

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._won_keys: set[str] = set()
        self._winners: list[User] = []
        self._rng = rng if rng is not None else random.Random()
        # Results (True = contained a Cheng Ru Group member) of the most recent
        # draws by the fallback trigger persons, at most the last two kept.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        """Users who have won so far, in winning order."""
        return list(self._winners)

    def is_winner(self, user: User) -> bool:
        return _user_key(user) in self._won_keys

    def is_fallback_active(self) -> bool:
        """True when the last two trigger-person draws had no Cheng Ru member."""
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the participants that may be drawn for the given prize."""
        available = [user for user in self._users if not self.is_winner(user)]
        drawer = prize.associated_drawer

        if drawer and _same(drawer, SPECIAL_DRAWER_LI_BIN):
            return available

        if drawer and _same(drawer, FALLBACK_TARGET_DRAWER) and self.is_fallback_active():
            return [user for user in available if _is_cheng_ru(user)]

        avoided = {group.strip().casefold() for group in prize.avoid_groups}
        return [
            user
            for user in available
            if user.department.strip().casefold() not in avoided
        ]

    def eligible_count(self, prize: Prize) -> int:
        """Number of participants currently eligible for the prize."""
        return len(self._get_eligible_pool(prize))

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._won_keys.add(_user_key(user))
        self._winners.append(user)

        drawer = prize.associated_drawer
        if drawer and any(_same(drawer, trigger) for trigger in FALLBACK_TRIGGER_DRAWERS):
            self.last_two_draw_results.append(_is_cheng_ru(user))
            del self.last_two_draw_results[:-2]
        return user

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize."""
        rules = ["previous winners are excluded"]
        drawer = prize.associated_drawer
        if drawer and _same(drawer, SPECIAL_DRAWER_LI_BIN):
            rules.append("special rule for Li Bin: avoidance groups are NOT applied")
        elif drawer and _same(drawer, FALLBACK_TARGET_DRAWER) and self.is_fallback_active():
            rules.append(
                f"fallback active: only {CHENG_RU_GROUP} members are eligible "
                "(avoidance groups overridden)"
            )
        elif prize.avoid_groups:
            rules.append("avoided groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(rules) + "."
