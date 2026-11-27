"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
FALLBACK_DRAWER = "Ma Jiaqi"
TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_GROUP = "Cheng Ru Group"


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()
        self._rng = random.Random()

    def is_winner(self, user: User) -> bool:
        """Return True if the user has already won in any round."""
        return user.name in self._winner_names

    def _is_fallback_active(self, prize: Prize) -> bool:
        """Fallback applies when the lottery person is Ma Jiaqi and neither of the
        last two draws by Chen Qixian / Jin Duo contained Cheng Ru Group members."""
        return (
            prize.associated_drawer == FALLBACK_DRAWER
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the list of users who may win the given prize."""
        available = [user for user in self.users if not self.is_winner(user)]

        if self._is_fallback_active(prize):
            # Forced limitation, even if Cheng Ru Group is an avoidance group.
            return [user for user in available if user.department == PROTECTED_GROUP]

        if prize.associated_drawer == SPECIAL_DRAWER:
            # Special rule: only previous winners are filtered.
            return available

        avoided = set(prize.avoid_groups)
        return [user for user in available if user.department not in avoided]

    def draw_winner(self, prize: Prize) -> User | None:
        """Randomly draw one eligible winner for the prize, or None if none is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)

        if prize.associated_drawer in TRIGGER_DRAWERS:
            self.last_two_draw_results.append(winner.department == PROTECTED_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

        return winner

    @staticmethod
    def describe_rules(prize: Prize) -> str:
        """Build a human-readable description of the prize's lottery rules."""
        parts: list[str] = []
        drawer = prize.associated_drawer or "none"
        parts.append(f"Lottery person: {drawer}")

        if prize.associated_drawer == SPECIAL_DRAWER:
            parts.append("Special rule: only previous winners are excluded")
        else:
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            parts.append(f"Avoid groups: {groups}")

        if prize.associated_drawer == FALLBACK_DRAWER:
            parts.append(
                "Fallback: if the last two draws by Chen Qixian and Jin Duo contain "
                f"no {PROTECTED_GROUP} members, the pool is limited to {PROTECTED_GROUP} members"
            )

        parts.append("Previous winners are always excluded")
        return "; ".join(parts)
