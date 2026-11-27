"""Lottery rule engine: eligibility pools, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.default_data import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User, normalize_key

_FALLBACK_TRIGGER_DRAWERS = (normalize_key(CHEN_QIXIAN), normalize_key(JIN_DUO))
_FALLBACK_TARGET_DRAWER = normalize_key(MA_JIAQI)
_SPECIAL_DRAWER = normalize_key(LI_BIN)
_CHENG_RU_KEY = normalize_key(CHENG_RU_GROUP)


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        # Whether each recent draw by Chen Qixian / Jin Duo contained a Cheng Ru member.
        self.last_two_draw_results: list[bool] = []

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _name_key(user: User) -> str:
        return normalize_key(user.name)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize_key(user.department) == _CHENG_RU_KEY

    @staticmethod
    def _drawer_key(prize: Prize) -> str:
        return normalize_key(prize.associated_drawer or "")

    def is_winner(self, user: User) -> bool:
        """True if the user has already won any prize."""
        return self._name_key(user) in self._winner_keys

    def is_cheng_ru_protection_active(self, prize: Prize) -> bool:
        """Fallback: Ma Jiaqi's prize is restricted to Cheng Ru members when both
        recent Chen Qixian / Jin Duo draws contained no Cheng Ru member."""
        return (
            self._drawer_key(prize) == _FALLBACK_TARGET_DRAWER
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    # ----- rule engine ---------------------------------------------------
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return users who may be drawn for the given prize."""
        available = [user for user in self._users if not self.is_winner(user)]

        # Fallback (Cheng Ru group protection) overrides avoidance groups.
        if self.is_cheng_ru_protection_active(prize):
            protected = [user for user in available if self._is_cheng_ru(user)]
            if protected:
                return protected
            # No Cheng Ru member remains: the normal rules apply.

        # Special rule: Li Bin's prizes only exclude previous winners.
        if self._drawer_key(prize) == _SPECIAL_DRAWER:
            return available

        avoid = {normalize_key(group) for group in prize.avoid_groups}
        return [user for user in available if normalize_key(user.department) not in avoid]

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts = ["Previous winners are excluded"]
        if self.is_cheng_ru_protection_active(prize):
            parts.append(
                f"Cheng Ru Group protection active: only {CHENG_RU_GROUP} members "
                "are eligible (avoidance groups ignored)"
            )
        elif self._drawer_key(prize) == _SPECIAL_DRAWER:
            parts.append("special rule for Li Bin: avoidance groups do not apply")
        elif prize.avoid_groups:
            parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if prize.associated_drawer:
            parts.append(f"lottery person: {prize.associated_drawer}")
        return "; ".join(parts)

    # ----- drawing -------------------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_keys.add(self._name_key(winner))
        return winner

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Record the outcome of a finished (or terminated) round for fallback tracking."""
        if self._drawer_key(prize) in _FALLBACK_TRIGGER_DRAWERS:
            self.last_two_draw_results.append(any(self._is_cheng_ru(w) for w in winners))
            del self.last_two_draw_results[:-2]
