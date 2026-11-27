"""Lottery rule engine and draw execution."""

from __future__ import annotations

import random
from typing import Iterable

from lottery_system.constants import CHAIN_DRAWERS, CHENG_RU_GROUP, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager, Winner


class LotteryManager:
    """Applies lottery rules and performs draws."""

    def __init__(self, users: Iterable[User], rng: random.Random | None = None) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results (True = winner from Cheng Ru group) of the most recent draws
        # made by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    def get_available_users(self) -> list[User]:
        """Participants who have not won any prize yet (anti-duplication)."""
        return [user for user in self.users if not self.result_manager.has_won(user)]

    def is_fallback_active(self) -> bool:
        """True when the last two chain draws produced no Cheng Ru group winner."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        pool = self.get_available_users()
        drawer = prize.associated_drawer

        # Fallback (Cheng Ru group protection) overrides everything else for Ma Jiaqi.
        if drawer == MA_JIAQI and self.is_fallback_active():
            return [user for user in pool if user.department == CHENG_RU_GROUP]

        # Special rule for Li Bin: only previous winners are excluded.
        if drawer == LI_BIN:
            return pool

        avoid = set(prize.avoid_groups)
        return [user for user in pool if user.department not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def describe_rules(self, prize: Prize) -> str:
        """Human readable description of the rules applied to a prize round."""
        parts: list[str] = []
        drawer = prize.associated_drawer
        if drawer:
            parts.append(f"Associated lottery person: {drawer}")
        else:
            parts.append("No associated lottery person")

        if drawer == LI_BIN:
            parts.append("Special rule: only previous winners are excluded (avoid groups not applied)")
        elif prize.avoid_groups:
            parts.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoided groups")

        if drawer == MA_JIAQI:
            if self.is_fallback_active():
                parts.append(
                    f"Fallback active: only {CHENG_RU_GROUP} members are eligible"
                )
            else:
                parts.append("Fallback inactive: Cheng Ru group protection not triggered")

        parts.append("Previous winners are always excluded")
        return "; ".join(parts)

    def _record_draw_result(self, hit_cheng_ru: bool) -> None:
        self.last_two_draw_results.append(hit_cheng_ru)
        self.last_two_draw_results = self.last_two_draw_results[-2:]

    def draw_one(self, prize: Prize) -> Winner | None:
        """Draw a single winner for the prize. Returns None if no eligible person remains."""
        pool = self._get_eligible_pool(prize)
        winner: Winner | None = None
        if pool:
            user = self._rng.choice(pool)
            winner = self.result_manager.add_winner(user, prize)

        if prize.associated_drawer in CHAIN_DRAWERS:
            hit = winner is not None and winner.user.department == CHENG_RU_GROUP
            self._record_draw_result(hit)
        return winner
