"""Lottery rule engine: eligibility filtering, special rules and fallback."""

from __future__ import annotations

import random

from lottery_system.constants import (
    CHENG_RU_GROUP,
    CHEN_QIXIAN,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    normalize_text,
)
from lottery_system.models import Prize, User

FALLBACK_SOURCE_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
FALLBACK_TARGET_DRAWER = MA_JIAQI
FALLBACK_WINDOW = 2


class LotteryManager:
    """Draws winners while applying the lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users = list(users)
        self._drawn_names: set[str] = set()
        self._rng = rng or random.Random()
        # Results (True = contains Cheng Ru Group member) of the most recent draws
        # by the consecutive lottery persons (Chen Qixian, Jin Duo).
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _is_drawer(prize: Prize, drawer: str) -> bool:
        return normalize_text(prize.associated_drawer or "") == normalize_text(drawer)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)

    def is_fallback_active(self, prize: Prize) -> bool:
        """True when Ma Jiaqi's prize pool is forced to Cheng Ru Group members."""
        return (
            self._is_drawer(prize, FALLBACK_TARGET_DRAWER)
            and len(self.last_two_draw_results) == FALLBACK_WINDOW
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return participants eligible for the next draw of the given prize."""
        # Anti-duplication: previous winners are always excluded.
        pool = [user for user in self._users if user.name not in self._drawn_names]

        # Fallback (Cheng Ru group protection) overrides avoidance groups.
        if self.is_fallback_active(prize):
            return [user for user in pool if self._is_cheng_ru(user)]

        # Special rule for Li Bin: relaxed filtering (avoidance groups not applied).
        if self._is_drawer(prize, LI_BIN):
            return pool

        avoided = {normalize_text(group) for group in prize.avoid_groups}
        return [user for user in pool if normalize_text(user.department) not in avoided]

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one winner for the prize; returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._drawn_names.add(user.name)
        self._record_draw(prize, user)
        return user

    def _record_draw(self, prize: Prize, user: User) -> None:
        if self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            # The protection window is consumed by Ma Jiaqi's draw.
            self.last_two_draw_results.clear()
        elif any(self._is_drawer(prize, drawer) for drawer in FALLBACK_SOURCE_DRAWERS):
            self.last_two_draw_results.append(self._is_cheng_ru(user))
            del self.last_two_draw_results[:-FALLBACK_WINDOW]

    def is_drawn(self, user: User) -> bool:
        """True if the user has already won a prize in this lottery."""
        return user.name in self._drawn_names

    def describe_rules(self, prize: Prize) -> list[str]:
        """Human-readable description of the rules applying to a prize round."""
        rules = ["Previous winners are excluded (no one wins twice)."]
        drawer = prize.associated_drawer
        if drawer:
            rules.append(f"Lottery person: {drawer}")
        if self._is_drawer(prize, LI_BIN):
            rules.append(
                "Special rule (Li Bin): relaxed filtering, avoidance groups are not applied."
            )
        elif prize.avoid_groups:
            rules.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        if self.is_fallback_active(prize):
            rules.append(
                f"Fallback protection active: only {CHENG_RU_GROUP} members are eligible."
            )
        return rules
