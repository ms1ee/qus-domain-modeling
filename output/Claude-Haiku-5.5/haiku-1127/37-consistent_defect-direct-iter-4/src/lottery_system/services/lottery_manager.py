"""Lottery rule engine and draw control."""

from __future__ import annotations

import random

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User, normalize_key


def _in_group(user: User, group: str) -> bool:
    return normalize_key(user.department) == normalize_key(group)


def _same_person(a: str | None, b: str) -> bool:
    return normalize_key(a or "") == normalize_key(b)


class LotteryManager:
    """Applies lottery rules and tracks winners across all rounds."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winners: list[User] = []
        self._winner_keys: set[str] = set()
        self._rng = rng or random.Random()
        self._current_prize: Prize | None = None
        self._round_winners: list[User] = []
        # Results of the two most recent rounds run by Chen Qixian / Jin Duo.
        # True means that round contained a Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        """All winners drawn so far, in winning order."""
        return list(self._winners)

    def _is_winner(self, user: User) -> bool:
        return normalize_key(user.name) in self._winner_keys

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the candidates eligible for the next pick of ``prize``."""
        base = [user for user in self._users if not self._is_winner(user)]
        drawer = prize.associated_drawer

        # Special rule: Li Bin only filters previous winners.
        if _same_person(drawer, LI_BIN):
            return base

        # Cheng Ru group protection for Ma Jiaqi's prize pool.
        if _same_person(drawer, MA_JIAQI) and self.last_two_draw_results == [False, False]:
            forced = [user for user in base if _in_group(user, CHENG_RU_GROUP)]
            if forced:
                return forced

        # Avoidance groups: their members remain eligible but are drawn after
        # all other members.
        preferred = [
            user
            for user in base
            if not any(_in_group(user, group) for group in prize.avoid_groups)
        ]
        if preferred:
            return preferred
        return base

    def start_round(self, prize: Prize) -> None:
        """Begin a lottery round for ``prize``."""
        self._current_prize = prize
        self._round_winners = []

    def draw_next(self) -> User | None:
        """Draw one winner for the active round. Returns None if no candidate."""
        if self._current_prize is None:
            raise RuntimeError("No active round. Call start_round() first.")
        pool = self._get_eligible_pool(self._current_prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winners.append(user)
        self._winner_keys.add(normalize_key(user.name))
        self._round_winners.append(user)
        return user

    def end_round(self) -> list[User]:
        """Finish the active round and return its winners."""
        if self._current_prize is None:
            return []
        prize = self._current_prize
        if _same_person(prize.associated_drawer, CHEN_QIXIAN) or _same_person(
            prize.associated_drawer, JIN_DUO
        ):
            hit = any(_in_group(user, CHENG_RU_GROUP) for user in self._round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

        result = list(self._round_winners)
        self._current_prize = None
        self._round_winners = []
        return result
