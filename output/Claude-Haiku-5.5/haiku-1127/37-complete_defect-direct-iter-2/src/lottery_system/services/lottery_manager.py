"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)


class LotteryManager:
    """Draws winners for prizes while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_names: set[str] = set()
        # Records whether each recent round of Chen Qixian / Jin Duo contained a
        # Cheng Ru Group member. Only the last two entries are kept.
        self.last_two_draw_results: list[bool] = []

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return (
            prize.associated_drawer is not None
            and prize.associated_drawer.strip().casefold() == drawer_name.casefold()
        )

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return user.department.strip().casefold() == CHENG_RU_GROUP.casefold()

    def has_won(self, user: User) -> bool:
        """Return True if the person has already won any prize."""
        return user.name in self._winner_names

    def _protection_active(self) -> bool:
        """Fallback is triggered when the last two Chen/Jin results both lack Cheng Ru members."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    # ------------------------------------------------------------------ rules
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the candidate pool for a prize round."""
        # Basic filtering: exclude all previous winners (any prize type).
        pool = [user for user in self.users if not self.has_won(user)]

        # Special rule: Li Bin only filters previous winners.
        if self._is_drawer(prize, LI_BIN):
            return pool

        # Fallback (Cheng Ru group protection): forced to Cheng Ru members,
        # overriding the prize's avoidance groups.
        if self._is_drawer(prize, MA_JIAQI) and self._protection_active():
            return [user for user in pool if self._is_cheng_ru(user)]

        # Group avoidance rule.
        avoid = {group.strip().casefold() for group in prize.avoid_groups if group and group.strip()}
        if avoid:
            pool = [user for user in pool if user.department.strip().casefold() not in avoid]
        return pool

    def count_eligible(self, prize: Prize) -> int:
        """Number of candidates currently eligible for the prize."""
        return len(self._get_eligible_pool(prize))

    def describe_rules(self, prize: Prize) -> str:
        """Human readable description of the rules applied to a prize round."""
        rules: list[str] = []
        if prize.associated_drawer:
            rules.append(f"lottery person: {prize.associated_drawer}")
        rules.append("previous winners are excluded")
        if self._is_drawer(prize, LI_BIN):
            rules.append("special rule for Li Bin: avoidance groups are not applied")
        elif self._is_drawer(prize, MA_JIAQI) and self._protection_active():
            rules.append(
                f"fallback active: only {CHENG_RU_GROUP} members are eligible "
                "(avoidance groups overridden)"
            )
        elif prize.avoid_groups:
            rules.append("avoid groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(rules)

    # ------------------------------------------------------------------ drawing
    def draw_next(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        self._winner_names.add(user.name)
        return user

    def complete_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Finish a round and update the fallback history for Chen Qixian / Jin Duo rounds."""
        if prize.associated_drawer is None:
            return
        if self._is_drawer(prize, CHEN_QIXIAN) or self._is_drawer(prize, JIN_DUO):
            hit = any(self._is_cheng_ru(user) for user in round_winners)
            self.last_two_draw_results.append(hit)
            del self.last_two_draw_results[:-2]
