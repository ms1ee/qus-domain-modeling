"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.config import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    FALLBACK_HISTORY_SIZE,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


def _normalize(value: str) -> str:
    return (value or "").strip().casefold()


def _is_drawer(prize: Prize, drawer_name: str) -> bool:
    return _normalize(prize.associated_drawer or "") == _normalize(drawer_name)


def _is_cheng_ru_member(user: User) -> bool:
    return _normalize(user.department) == _normalize(CHENG_RU_GROUP)


class LotteryManager:
    """Runs lottery draws while enforcing all eligibility rules.

    Rules:
    - Previous winners are never drawn again (anti-duplication, any prize).
    - Members of the prize's avoidance groups are excluded.
    - Lottery person "Li Bin": only previous winners are excluded.
    - Fallback (Cheng Ru group protection): if the last two draws by Chen Qixian / Jin Duo
      both contained no Cheng Ru Group winner, the next Ma Jiaqi prize is limited to
      Cheng Ru Group members (overriding avoidance groups). The protection is consumed
      after the Ma Jiaqi round is finished.
    """

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self._rng = rng or random.Random()
        self._round_hit_cheng_ru = False
        # Results (True = contained a Cheng Ru Group member) of the most recent draws
        # by Chen Qixian / Jin Duo, oldest first.
        self.last_two_draw_results: list[bool] = []

    @property
    def winner_names(self) -> frozenset[str]:
        return frozenset(self._winner_names)

    def is_cheng_ru_fallback_active(self, prize: Prize) -> bool:
        """True if the Cheng Ru group protection applies to this prize."""
        return (
            _is_drawer(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == FALLBACK_HISTORY_SIZE
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [user for user in self._users if user.name not in self._winner_names]

        if _is_drawer(prize, LI_BIN):
            return available

        if self.is_cheng_ru_fallback_active(prize):
            cheng_ru = [user for user in available if _is_cheng_ru_member(user)]
            if cheng_ru:
                return cheng_ru

        avoid = {_normalize(group) for group in (prize.avoid_groups or [])}
        return [user for user in available if _normalize(user.department) not in avoid]

    def get_eligible_count(self, prize: Prize) -> int:
        """Number of users currently eligible for the prize."""
        return len(self._get_eligible_pool(prize))

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize."""
        if _is_drawer(prize, LI_BIN):
            return (
                "Special rule (Li Bin): only previous winners are excluded; "
                "avoidance groups do not apply."
            )
        parts = ["previous winners are excluded"]
        if prize.avoid_groups:
            parts.append("avoidance group(s) excluded: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if _is_drawer(prize, MA_JIAQI):
            if self.is_cheng_ru_fallback_active(prize):
                parts.append(
                    "Cheng Ru Group protection ACTIVE: only Cheng Ru Group members are "
                    "eligible (overrides avoidance groups)"
                )
            else:
                parts.append(
                    "Cheng Ru Group protection inactive (applies if the last two "
                    "Chen Qixian/Jin Duo draws had no Cheng Ru Group winner)"
                )
        return "; ".join(parts)

    def begin_round(self, prize: Prize) -> None:
        """Start tracking a new lottery round."""
        self._round_hit_cheng_ru = False

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_names.add(user.name)
        if _is_cheng_ru_member(user):
            self._round_hit_cheng_ru = True
        return user

    def end_round(self, prize: Prize) -> None:
        """Finish the round and update the fallback history."""
        if _is_drawer(prize, CHEN_QIXIAN) or _is_drawer(prize, JIN_DUO):
            self.last_two_draw_results.append(self._round_hit_cheng_ru)
            del self.last_two_draw_results[:-FALLBACK_HISTORY_SIZE]
        elif self.is_cheng_ru_fallback_active(prize):
            self.last_two_draw_results.clear()
        self._round_hit_cheng_ru = False
