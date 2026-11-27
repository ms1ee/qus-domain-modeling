"""Lottery rule engine: eligibility filtering, avoidance, fallback and draws."""

from __future__ import annotations

import random

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Whether each of the two most recent draws by Chen Qixian / Jin Duo
        # produced a Cheng Ru group member (True) or not (False).
        self.last_two_draw_results: list[bool] = []

    # ----- state helpers -------------------------------------------------
    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def _non_winners(self) -> list[User]:
        return [u for u in self._users if u.name not in self._winner_names]

    def _fallback_triggered(self) -> bool:
        """True when the last two lottery-person draws had no Cheng Ru winners."""
        return len(self.last_two_draw_results) >= 2 and not any(
            self.last_two_draw_results[-2:]
        )

    # ----- rule engine ---------------------------------------------------
    def _build_tiers(self, prize: Prize) -> list[list[User]]:
        """Return candidate tiers in priority order; earlier tiers are drawn first."""
        candidates = self._non_winners()
        drawer = prize.associated_drawer

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members
        # (ignoring avoidance groups) when the protection condition holds.
        if drawer == MA_JIAQI and self._fallback_triggered():
            cheng_ru = [u for u in candidates if u.department == CHENG_RU_GROUP]
            if cheng_ru:
                return [cheng_ru]

        # Special rule: Li Bin only filters previous winners.
        if drawer == LI_BIN:
            return [candidates]

        # Standard rule: avoidance-group members are eligible but drawn last.
        avoid = set(prize.avoid_groups)
        primary = [u for u in candidates if u.department not in avoid]
        secondary = [u for u in candidates if u.department in avoid]
        return [primary, secondary]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the currently drawable pool (the highest-priority non-empty tier)."""
        for tier in self._build_tiers(prize):
            if tier:
                return list(tier)
        return []

    def _record_draw(self, prize: Prize, user: User) -> None:
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            self.last_two_draw_results.append(user.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI:
            # The protection window is consumed by Ma Jiaqi's draw.
            self.last_two_draw_results = []

    # ----- public draw API -----------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize; returns None when no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winner_names.add(user.name)
        self._record_draw(prize, user)
        return user
