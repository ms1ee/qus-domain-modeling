"""Lottery rule engine: eligibility pools, fallback protection and draws."""

from __future__ import annotations

import random

from ..models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize,
)


class LotteryManager:
    """Runs draws for a set of users while enforcing lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self._rng = rng or random.Random()
        self.winners: list[User] = []
        # Each entry: whether the result of a consecutive lottery person
        # (Chen Qixian or Jin Duo) contained any Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    # ----- helpers -----
    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize(user.department) == normalize(CHENG_RU_GROUP)

    def _available_users(self) -> list[User]:
        """Users who have not won yet (anti-duplication)."""
        return [u for u in self._users if normalize(u.name) not in self._winner_keys]

    def _fallback_active(self) -> bool:
        """True when the last two lottery persons' results contained no Cheng Ru members."""
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def is_winner(self, user: User) -> bool:
        return normalize(user.name) in self._winner_keys

    # ----- rule engine -----
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users eligible to win the given prize in the current draw."""
        available = self._available_users()
        drawer = normalize(prize.associated_drawer) if prize.associated_drawer else ""

        # Special rule: Li Bin only filters previous winners.
        if drawer == normalize(LI_BIN):
            return available

        # Fallback (Cheng Ru group protection) for Ma Jiaqi's prizes.
        if drawer == normalize(MA_JIAQI) and self._fallback_active():
            protected = [u for u in available if self._is_cheng_ru(u)]
            if protected:
                return protected

        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in available if normalize(u.department) not in avoid]

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_keys.add(normalize(user.name))
        self.winners.append(user)
        return user

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Record the outcome of a finished round for fallback tracking."""
        drawer = normalize(prize.associated_drawer) if prize.associated_drawer else ""
        if drawer in (normalize(CHEN_QIXIAN), normalize(JIN_DUO)):
            contains_cheng_ru = any(self._is_cheng_ru(u) for u in round_winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
