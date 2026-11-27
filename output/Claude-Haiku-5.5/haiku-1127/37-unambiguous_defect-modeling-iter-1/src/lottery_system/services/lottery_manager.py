"""Lottery rule engine: filtering, special rules, fallback and anti-duplication."""

from __future__ import annotations

import random

from lottery_system.config import (
    CHENG_RU_GROUP,
    FALLBACK_DRAWER,
    FALLBACK_TRIGGER_DRAWERS,
    LI_BIN,
)
from lottery_system.models import Prize, User


class LotteryManager:
    """Performs individual draws while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Whether each recent draw by Chen Qixian / Jin Duo contained a Cheng Ru
        # group member. Only the last two results are kept.
        self.last_two_draw_results: list[bool] = []

    @property
    def winner_names(self) -> frozenset[str]:
        """Names of everyone who has won so far (anti-duplication record)."""
        return frozenset(self._winner_names)

    def is_fallback_active(self) -> bool:
        """True when neither of the last two trigger draws hit the Cheng Ru group."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the candidates eligible for the given prize right now."""
        # Anti-duplication: previous winners are always excluded.
        available = [user for user in self._users if user.name not in self._winner_names]

        drawer = prize.associated_drawer

        # Special rule: Li Bin gets relaxed filtering (avoidance groups ignored).
        if drawer == LI_BIN:
            return available

        # Fallback: Cheng Ru group protection overrides avoidance groups.
        if drawer == FALLBACK_DRAWER and self.is_fallback_active():
            protected = [user for user in available if user.department == CHENG_RU_GROUP]
            if protected:
                return protected

        # Basic filtering: exclude members of the prize's avoidance groups.
        return [user for user in available if user.department not in prize.avoid_groups]

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        winner = random.choice(pool)
        self._winner_names.add(winner.name)

        if prize.associated_drawer in FALLBACK_TRIGGER_DRAWERS:
            self.last_two_draw_results.append(winner.department == CHENG_RU_GROUP)
            del self.last_two_draw_results[:-2]

        return winner

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        rules = ["Excludes previous winners"]
        drawer = prize.associated_drawer

        if drawer == LI_BIN:
            rules.append("Relaxed filtering for Li Bin (avoidance groups not applied)")
        elif prize.avoid_groups:
            rules.append("Avoids groups: " + ", ".join(prize.avoid_groups))

        if drawer == FALLBACK_DRAWER and self.is_fallback_active():
            rules.append(f"Fallback protection active: only {CHENG_RU_GROUP} members eligible")

        if drawer:
            rules.append(f"Lottery person: {drawer}")
        else:
            rules.append("No associated lottery person")
        return "; ".join(rules)
