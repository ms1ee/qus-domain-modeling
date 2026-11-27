"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random
from typing import Optional

from lottery_system.models import (
    CHEN_QIXIAN,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    is_cheng_ru_group,
    normalize_group,
    same_text,
)

# Lottery persons whose draw outcomes feed the Cheng Ru group protection check.
FALLBACK_TRIGGER_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
# Lottery person whose prize pool is forced to Cheng Ru group when fallback is active.
FALLBACK_TARGET_DRAWER = MA_JIAQI


class LotteryManager:
    """Maintains winners across rounds and applies the lottery rules."""

    def __init__(self, users: list[User], rng: Optional[random.Random] = None) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self._winners: list[User] = []
        self._rng = rng if rng is not None else random.Random()
        # Outcome per completed round of Chen Qixian / Jin Duo prizes:
        # True if that round produced at least one Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        """All winners drawn so far, in drawing order."""
        return list(self._winners)

    def is_fallback_active(self) -> bool:
        """Fallback is active when the last two Chen Qixian/Jin Duo results both had no Cheng Ru member."""
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def _is_fallback_for(self, prize: Prize) -> bool:
        return same_text(prize.associated_drawer, FALLBACK_TARGET_DRAWER) and self.is_fallback_active()

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the eligible pool for a prize under the rule engine."""
        base = [user for user in self._users if user.name not in self._winner_names]

        # Special rule: Li Bin only filters previous winners.
        if same_text(prize.associated_drawer, LI_BIN):
            return base

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group (overrides avoidance groups).
        if self._is_fallback_for(prize):
            return [user for user in base if is_cheng_ru_group(user.department)]

        # Standard rule: exclude previous winners and avoidance groups.
        avoided = {normalize_group(group) for group in prize.avoid_groups}
        return [user for user in base if normalize_group(user.department) not in avoided]

    def eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rule applied to a prize round."""
        drawer = prize.associated_drawer
        if same_text(drawer, LI_BIN):
            return (
                "Only previous winners are excluded; avoidance groups are not applied "
                "(lottery person: Li Bin)."
            )
        if self._is_fallback_for(prize):
            return (
                "Cheng Ru Group protection active: only Cheng Ru Group members are eligible "
                "(avoidance groups overridden)."
            )
        parts = ["Previous winners are excluded"]
        if prize.avoid_groups:
            parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        if drawer:
            parts.append(f"lottery person: {drawer}")
        return "; ".join(parts) + "."

    def draw_one(self, prize: Prize) -> Optional[User]:
        """Draw one winner for the prize. Returns None if no eligible participant exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        self._winners.append(winner)
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Record the outcome of a completed round for the fallback mechanism.

        Only rounds of Chen Qixian / Jin Duo that produced at least one winner are recorded.
        """
        if not round_winners:
            return
        drawer = prize.associated_drawer
        if any(same_text(drawer, name) for name in FALLBACK_TRIGGER_DRAWERS):
            hit = any(is_cheng_ru_group(user.department) for user in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
