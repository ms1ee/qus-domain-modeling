"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random
from collections.abc import Iterable

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize,
)
from lottery_system.services.result_manager import ResultManager


def _is_cheng_ru(user: User) -> bool:
    return normalize(user.department) == normalize(CHENG_RU_GROUP)


class LotteryManager:
    """Runs lottery draws according to the rule engine."""

    def __init__(
        self,
        users: Iterable[User],
        result_manager: ResultManager | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.users: list[User] = list(users)
        self.result_manager: ResultManager = result_manager or ResultManager()
        # Per-round results of the lottery persons Chen Qixian / Jin Duo:
        # True means that round's winners contained a Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng or random.Random()

    # ----- rule engine -------------------------------------------------

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may still be drawn for the given prize."""
        taken = {normalize(w.user.name) for w in self.result_manager.winners}
        pool = [u for u in self.users if normalize(u.name) not in taken]

        drawer = normalize(prize.associated_drawer or "")

        # Special rule: Li Bin's prizes use relaxed filtering (no avoidance groups).
        if drawer == normalize(LI_BIN):
            return pool

        # Fallback (Cheng Ru group protection) for Ma Jiaqi's prize.
        if drawer == normalize(MA_JIAQI) and self.fallback_active():
            return [u for u in pool if _is_cheng_ru(u)]

        # Basic filtering: exclude members of the prize's avoidance groups.
        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in pool if normalize(u.department) not in avoid]

    def eligible_candidates(self, prize: Prize) -> list[User]:
        """Public wrapper returning the current eligible pool for a prize."""
        return self._get_eligible_pool(prize)

    def fallback_active(self) -> bool:
        """True when the last two lottery-person rounds both had no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    # ----- draw process ------------------------------------------------

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None when no candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.result_manager.add_winner(user, prize)
        return user

    def complete_round(self, prize: Prize, round_winners: Iterable[User]) -> None:
        """Update fallback state after a round finishes."""
        winners = list(round_winners)
        drawer = normalize(prize.associated_drawer or "")

        if drawer in (normalize(CHEN_QIXIAN), normalize(JIN_DUO)) and winners:
            self.last_two_draw_results.append(any(_is_cheng_ru(u) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == normalize(MA_JIAQI):
            # The protection check is consumed by Ma Jiaqi's round.
            self.last_two_draw_results = []
