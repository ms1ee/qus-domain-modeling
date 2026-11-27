"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
RESULT_DRAWERS = ("Chen Qixian", "Jin Duo")


def _norm(text: str) -> str:
    return (text or "").strip().casefold()


class LotteryManager:
    """Applies lottery rules and draws winners for each prize."""

    def __init__(self, users):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results of the last two draws by Chen Qixian / Jin Duo.
        # True means that round produced at least one Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()

    # ----- rule helpers -------------------------------------------------
    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return _norm(prize.associated_drawer) == _norm(drawer_name)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return _norm(user.department) == _norm(CHENG_RU_GROUP)

    def _fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection: Ma Jiaqi's pool is forced to Cheng Ru members
        when neither of the last two Chen Qixian / Jin Duo results contained
        a Cheng Ru member."""
        return (
            self._is_drawer(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def is_winner(self, user: User) -> bool:
        return _norm(user.name) in self._winner_names

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return users who may still win the given prize."""
        candidates = [u for u in self.users if not self.is_winner(u)]

        # Special rule: Li Bin only filters previous winners.
        if self._is_drawer(prize, LI_BIN):
            return candidates

        # Fallback rule: forced to Cheng Ru members, overriding avoidance groups.
        if self._fallback_active(prize):
            return [u for u in candidates if self._is_cheng_ru(u)]

        # Basic rule: exclude previous winners and avoidance groups.
        avoided = {_norm(group) for group in prize.avoid_groups}
        return [u for u in candidates if _norm(u.department) not in avoided]

    def describe_rule(self, prize: Prize) -> str:
        """Human readable description of the rules applied to a prize round."""
        parts: list[str] = []
        if self._is_drawer(prize, LI_BIN):
            parts.append(
                "Special rule (Li Bin): only previous winners are excluded; "
                "avoidance groups do not apply."
            )
        elif self._fallback_active(prize):
            parts.append(
                "Fallback protection active: only Cheng Ru Group members are "
                "eligible (avoidance groups overridden)."
            )
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                parts.append("Avoided groups: " + ", ".join(prize.avoid_groups) + ".")
            else:
                parts.append("No avoidance groups.")
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}.")
        return " ".join(parts)

    # ----- drawing ------------------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_names.add(_norm(winner.name))
        self.result_manager.add_winner(winner, prize)
        return winner

    def record_round(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback state after a round has finished."""
        if self._is_drawer(prize, MA_JIAQI):
            # The fallback window is consumed by this round.
            self.last_two_draw_results = []
            return
        if any(self._is_drawer(prize, drawer) for drawer in RESULT_DRAWERS):
            has_cheng_ru = any(self._is_cheng_ru(u) for u in winners)
            self.last_two_draw_results = (self.last_two_draw_results + [has_cheng_ru])[-2:]
