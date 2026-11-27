"""Lottery rule engine: eligibility filtering, avoidance, special rules and fallback."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

PROTECTED_GROUP = "Cheng Ru Group"
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
SPECIAL_DRAWER = "Li Bin"


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


def is_protected_group(user: User) -> bool:
    """True if the user belongs to the protected 'Cheng Ru group'."""
    return _norm(user.department) == _norm(PROTECTED_GROUP)


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_names: set[str] = set()
        # Records, for the last two trigger-drawer rounds, whether the round
        # contained Cheng Ru group members (True) or not (False).
        self.last_two_draw_results: list[bool] = []
        self.draw_index: int = 0
        self.status: str = "idle"

    def has_won(self, user: User) -> bool:
        return _norm(user.name) in self._winner_names

    def _available(self) -> list[User]:
        """Users who have not won any prize yet (anti-duplication)."""
        return [user for user in self.users if not self.has_won(user)]

    def is_fallback_active(self, prize: Prize) -> bool:
        """Fallback applies to Ma Jiaqi's rounds when the last two trigger
        rounds (Chen Qixian / Jin Duo) both contained no Cheng Ru group members."""
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_TARGET_DRAWER)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _split_tiers(self, prize: Prize) -> tuple[list[User], list[User]]:
        """Return (primary_pool, deferred_pool).

        Primary pool is drawn first. Deferred pool holds members of the prize's
        avoidance groups and is only drawn after the primary pool is exhausted.
        """
        available = self._available()

        if self.is_fallback_active(prize):
            protected = [user for user in available if is_protected_group(user)]
            if protected:
                return protected, []

        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            # Special rule: only previous winners are filtered out.
            return available, []

        avoid = {_norm(group) for group in prize.avoid_groups}
        primary = [user for user in available if _norm(user.department) not in avoid]
        deferred = [user for user in available if _norm(user.department) in avoid]
        return primary, deferred

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """All users currently eligible for the prize, primary members first."""
        primary, deferred = self._split_tiers(prize)
        return primary + deferred

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        primary, deferred = self._split_tiers(prize)
        pool = primary or deferred
        if not pool:
            return None
        winner = random.choice(pool)
        self.winners.append(winner)
        self._winner_names.add(_norm(winner.name))
        self.draw_index += 1
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback history after a round has completed."""
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(name) for name in FALLBACK_TRIGGER_DRAWERS}:
            hit = any(is_protected_group(user) for user in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_TARGET_DRAWER):
            # The fallback has been consumed by this round.
            self.last_two_draw_results.clear()

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts: list[str] = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}.")
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            parts.append("Only previous winners are excluded; avoidance groups do not apply.")
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                groups = ", ".join(prize.avoid_groups)
                parts.append(
                    f"Members of avoidance group(s) [{groups}] are drawn after other members."
                )
        if self.is_fallback_active(prize):
            parts.append(
                f"Fallback active: only {PROTECTED_GROUP} members are eligible."
            )
        return " ".join(parts)
