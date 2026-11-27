"""Lottery rule engine: eligibility pools, Cheng Ru fallback, and winner tracking."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User, normalize
from lottery_system.services.result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru Group"

DRAWER_CHEN_QIXIAN = "Chen Qixian"
DRAWER_JIN_DUO = "Jin Duo"
DRAWER_MA_JIAQI = "Ma Jiaqi"
DRAWER_LI_BIN = "Li Bin"
DRAWER_OPTIONS: tuple[str, ...] = (DRAWER_CHEN_QIXIAN, DRAWER_JIN_DUO, DRAWER_MA_JIAQI, DRAWER_LI_BIN)

_HISTORY_DRAWERS: tuple[str, ...] = (DRAWER_CHEN_QIXIAN, DRAWER_JIN_DUO)


def is_cheng_ru_member(user: User) -> bool:
    """True if the user belongs to the Cheng Ru group."""
    return normalize(user.department) == normalize(CHENG_RU_GROUP)


def _is_drawer(prize: Prize, drawer: str) -> bool:
    return prize.associated_drawer is not None and normalize(prize.associated_drawer) == normalize(drawer)


def describe_prize_rule(prize: Prize, fallback_active: bool = False) -> str:
    """Build a human-readable description of the rules applied to a prize round."""
    if _is_drawer(prize, DRAWER_LI_BIN):
        parts = ["Only previous winners are excluded (group avoidance not applied)"]
    else:
        parts = ["Previous winners are excluded"]
        if prize.avoid_groups:
            parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("no group avoidance")
    if _is_drawer(prize, DRAWER_MA_JIAQI) and fallback_active:
        parts.append("Cheng Ru Group protection active: only Cheng Ru Group members are eligible")
    return "; ".join(parts) + "."


class LotteryManager:
    """Controls eligibility and winner bookkeeping for lottery rounds."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.last_two_draw_results: list[bool] = []
        self.result_manager = ResultManager()

    def has_won(self, user: User) -> bool:
        """True if this person has already won any prize."""
        return normalize(user.name) in self._winner_keys

    def is_cheng_ru_fallback_active(self) -> bool:
        """True when the last two lottery-person results both contain no Cheng Ru members."""
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def _is_cheng_ru_fallback_for(self, prize: Prize) -> bool:
        return _is_drawer(prize, DRAWER_MA_JIAQI) and self.is_cheng_ru_fallback_active()

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users eligible to win the given prize right now."""
        pool = [user for user in self._users if not self.has_won(user)]

        # Fallback (Cheng Ru group protection): limit to Cheng Ru members, overriding avoidance groups.
        if self._is_cheng_ru_fallback_for(prize):
            return [user for user in pool if is_cheng_ru_member(user)]

        # Special rule: Li Bin's prizes only exclude previous winners.
        if _is_drawer(prize, DRAWER_LI_BIN):
            return pool

        avoid = {normalize(group) for group in prize.avoid_groups}
        return [user for user in pool if normalize(user.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        """Describe the rules applied to the prize in the current state."""
        return describe_prize_rule(prize, self.is_cheng_ru_fallback_active())

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no eligible candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_keys.add(normalize(winner.name))
        self.result_manager.add_winner(winner, prize)
        return winner

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Record the outcome of a finished round for the fallback history."""
        if any(_is_drawer(prize, drawer) for drawer in _HISTORY_DRAWERS):
            contains_cheng_ru = any(is_cheng_ru_member(winner) for winner in winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
