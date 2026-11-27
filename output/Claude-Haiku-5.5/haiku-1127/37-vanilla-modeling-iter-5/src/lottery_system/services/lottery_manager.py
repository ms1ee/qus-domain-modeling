"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

import random

from ..config import (
    FALLBACK_DRAWER,
    FALLBACK_HISTORY_SIZE,
    FALLBACK_TRIGGER_DRAWERS,
    PROTECTED_GROUP,
    SPECIAL_RULE_DRAWER,
)
from ..models import Prize, User, normalize_key


def _is_same(a, b) -> bool:
    return a is not None and b is not None and normalize_key(a) == normalize_key(b)


class LotteryManager:
    """Runs lottery draws for a fixed participant list while enforcing rules."""

    def __init__(self, users) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.winners: list[User] = []
        # Results of the most recent draws by Chen Qixian / Jin Duo:
        # True means the round contained at least one Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _is_protected(user: User) -> bool:
        return normalize_key(user.department) == normalize_key(PROTECTED_GROUP)

    def has_won(self, user: User) -> bool:
        return normalize_key(user.name) in self._winner_keys

    def is_fallback_active(self, prize: Prize) -> bool:
        """Fallback applies when the prize is drawn by Ma Jiaqi and neither of
        the two most recent Chen Qixian / Jin Duo rounds contained Cheng Ru members."""
        return (
            _is_same(prize.associated_drawer, FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= FALLBACK_HISTORY_SIZE
            and not any(self.last_two_draw_results[-FALLBACK_HISTORY_SIZE:])
        )

    # ----- rule engine ---------------------------------------------------
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        # Anti-duplication: previous winners are always excluded.
        pool = [user for user in self._users if not self.has_won(user)]

        # Special rule for Li Bin: only previous winners are filtered.
        if _is_same(prize.associated_drawer, SPECIAL_RULE_DRAWER):
            return pool

        # Fallback (Cheng Ru group protection): restrict to Cheng Ru members,
        # even if that group is an avoidance group of this prize.
        if self.is_fallback_active(prize):
            return [user for user in pool if self._is_protected(user)]

        # Basic filtering: exclude members of avoidance groups.
        avoid = {normalize_key(group) for group in prize.avoid_groups}
        return [user for user in pool if normalize_key(user.department) not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        return self._get_eligible_pool(prize)

    def describe_rule(self, prize: Prize) -> str:
        drawer = prize.associated_drawer or "None"
        parts = [f"Lottery person: {drawer}"]
        if _is_same(prize.associated_drawer, SPECIAL_RULE_DRAWER):
            parts.append("only previous winners are excluded (special rule, avoid groups not applied)")
        elif self.is_fallback_active(prize):
            parts.append(
                f"previous winners excluded; fallback active: only '{PROTECTED_GROUP}' members "
                "eligible (avoid groups overridden)"
            )
        else:
            parts.append("previous winners excluded")
            if prize.avoid_groups:
                parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
            else:
                parts.append("no avoid groups")
        return "; ".join(parts)

    # ----- drawing -------------------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winner_keys.add(normalize_key(user.name))
        self.winners.append(user)
        return user

    def finish_round(self, prize: Prize, round_winners) -> None:
        """Update fallback history after a round completes."""
        drawer = prize.associated_drawer
        if _is_same(drawer, FALLBACK_DRAWER):
            # Fallback opportunity is consumed by Ma Jiaqi's round.
            self.last_two_draw_results = []
            return
        if any(_is_same(drawer, trigger) for trigger in FALLBACK_TRIGGER_DRAWERS):
            hit = any(self._is_protected(user) for user in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-FALLBACK_HISTORY_SIZE:]
