"""Lottery rule engine: eligibility filtering, fallback protection and winner tracking."""

from __future__ import annotations

import random

from lottery_system.config import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User


def normalize_text(text: str) -> str:
    """Normalize names/groups for comparison (whitespace and case insensitive)."""
    return " ".join(text.split()).casefold()


def is_cheng_ru_member(user: User) -> bool:
    """True if the user belongs to the Cheng Ru group."""
    return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)


class LotteryManager:
    """Runs the eligibility rules and records winners in real time."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Whether each recent Chen Qixian / Jin Duo round contained a Cheng Ru member.
        # True = contained a Cheng Ru member; only the last two results are kept.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    def has_won(self, user: User) -> bool:
        """True if the person has already won any prize."""
        return user.name in self._winner_names

    def is_fallback_active(self) -> bool:
        """Fallback applies when the last two draw results both lack Cheng Ru members."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the users eligible to win the given prize right now."""
        pool = [user for user in self._users if not self.has_won(user)]
        drawer = prize.associated_drawer

        if drawer == LI_BIN:
            # Special rule: only previous winners are filtered out.
            return pool

        if drawer == MA_JIAQI and self.is_fallback_active():
            # Fallback: forcibly limit to Cheng Ru group members, overriding avoidance groups.
            return [user for user in pool if is_cheng_ru_member(user)]

        avoided = {normalize_text(group) for group in prize.avoid_groups}
        return [user for user in pool if normalize_text(user.department) not in avoided]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        return winner

    def complete_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback state after a round has finished."""
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            contains_cheng_ru = any(is_cheng_ru_member(user) for user in round_winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI and self.is_fallback_active():
            # The fallback protection has been consumed by this round.
            self.last_two_draw_results = []
