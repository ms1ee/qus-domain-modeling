"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
PROTECTED_DRAWERS = frozenset({"Chen Qixian", "Jin Duo"})


def _is_cheng_ru(user: User) -> bool:
    return user.department.casefold() == CHENG_RU_GROUP.casefold()


class LotteryManager:
    """Draws winners while enforcing the lottery rules.

    Rules:
    - Previous winners are never drawn again.
    - Members of a prize's avoidance groups are drawn only after all other
      eligible members (they remain eligible).
    - Lottery person 'Li Bin' only filters previous winners; avoidance groups
      are not applied.
    - Fallback: if neither of the last two draws made by Chen Qixian / Jin Duo
      produced a Cheng Ru Group member, Ma Jiaqi's pool is limited to Cheng Ru
      Group members (even if that group is an avoidance group).
    """

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self.winners: list[User] = []
        self.last_two_draw_results: list[bool] = []

    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def is_cheng_ru_fallback_active(self) -> bool:
        """True when the last two protected draws both produced no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users the next draw for this prize should be taken from."""
        candidates = [user for user in self._users if user.name not in self._winner_names]

        if prize.associated_drawer == MA_JIAQI and self.is_cheng_ru_fallback_active():
            protected = [user for user in candidates if _is_cheng_ru(user)]
            if protected:
                return protected

        if prize.associated_drawer == LI_BIN:
            return candidates

        avoid = {group.casefold() for group in prize.avoid_groups}
        non_avoid = [user for user in candidates if user.department.casefold() not in avoid]
        avoid_members = [user for user in candidates if user.department.casefold() in avoid]
        return non_avoid if non_avoid else avoid_members

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None when no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        winner = random.choice(pool)
        self._winner_names.add(winner.name)
        self.winners.append(winner)

        if prize.associated_drawer in PROTECTED_DRAWERS:
            self.last_two_draw_results.append(_is_cheng_ru(winner))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts = ["previous winners are excluded"]
        if prize.associated_drawer == LI_BIN:
            parts.append("special rule for Li Bin: only previous winners are filtered, avoidance groups not applied")
        else:
            if prize.avoid_groups:
                parts.append(
                    "avoidance groups (" + ", ".join(prize.avoid_groups)
                    + ") are drawn only after other members"
                )
        if prize.associated_drawer == MA_JIAQI:
            parts.append(
                "fallback: if neither of the last two Chen Qixian/Jin Duo draws "
                "produced a Cheng Ru Group member, the pool is limited to Cheng Ru Group members"
            )
        return "; ".join(parts)
