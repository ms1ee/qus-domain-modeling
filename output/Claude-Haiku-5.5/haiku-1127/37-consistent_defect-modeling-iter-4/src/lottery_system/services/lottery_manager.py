"""Lottery rule engine: eligibility, avoidance, special rules and fallback."""

from __future__ import annotations

import random

from lottery_system.constants import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager
from lottery_system.utils import contains_group, same_text


class LotteryManager:
    """Executes lottery draws according to the configured rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Cheng Ru group results (True = winners contained a Cheng Ru member)
        # of the most recent rounds conducted by Chen Qixian or Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._rng = random.Random()

    @property
    def users(self) -> list[User]:
        return list(self._users)

    # ----- helpers -------------------------------------------------------

    def _remaining(self) -> list[User]:
        """Participants who have not won any prize yet."""
        return [user for user in self._users if not self.result_manager.has_won(user)]

    @staticmethod
    def _drawer_is(prize: Prize, name: str) -> bool:
        return prize.associated_drawer is not None and same_text(prize.associated_drawer, name)

    def _is_li_bin_round(self, prize: Prize) -> bool:
        return self._drawer_is(prize, LI_BIN)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return same_text(user.department, CHENG_RU_GROUP)

    @staticmethod
    def _is_avoided(user: User, prize: Prize) -> bool:
        return contains_group(user.department, prize.avoid_groups)

    def _is_fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection: Ma Jiaqi's pool is forced to Cheng Ru members
        when the last two Chen Qixian / Jin Duo results had no Cheng Ru member."""
        return (
            self._drawer_is(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    # ----- eligibility ---------------------------------------------------

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Primary eligible pool (excludes previous winners and avoidance groups)."""
        remaining = self._remaining()
        if self._is_fallback_active(prize):
            return [user for user in remaining if self._is_cheng_ru(user)]
        if self._is_li_bin_round(prize):
            return remaining
        return [user for user in remaining if not self._is_avoided(user, prize)]

    def _get_avoidance_pool(self, prize: Prize) -> list[User]:
        """Avoidance-group members, drawn only after the primary pool is exhausted."""
        if self._is_fallback_active(prize) or self._is_li_bin_round(prize):
            return []
        return [user for user in self._remaining() if self._is_avoided(user, prize)]

    # ----- drawing -------------------------------------------------------

    def draw_next(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_avoidance_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self.result_manager.add_winner(winner, prize)
        return winner

    def complete_round(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback history after a round finishes."""
        if self._drawer_is(prize, CHEN_QIXIAN) or self._drawer_is(prize, JIN_DUO):
            round_has_cheng_ru = any(self._is_cheng_ru(user) for user in winners)
            self.last_two_draw_results.append(round_has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def rule_description(self, prize: Prize) -> str:
        """Human-readable description of the rules for a round."""
        parts: list[str] = []
        if self._is_li_bin_round(prize):
            parts.append("Only previous winners are excluded; avoidance groups do not apply.")
        elif self._is_fallback_active(prize):
            parts.append(
                "Cheng Ru Group protection active: only Cheng Ru Group members are eligible."
            )
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                parts.append(
                    "Members of avoidance groups ("
                    + ", ".join(prize.avoid_groups)
                    + ") are drawn only after other members."
                )
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}.")
        return " ".join(parts)
