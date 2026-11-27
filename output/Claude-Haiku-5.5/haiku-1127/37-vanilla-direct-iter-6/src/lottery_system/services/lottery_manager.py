"""Lottery rule engine: candidate filtering, fallback protection and draws."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager


CHENG_RU_GROUP = "cheng ru group"
LI_BIN = "li bin"
MA_JIAQI = "ma jiaqi"
FALLBACK_DRAWERS = frozenset({"chen qixian", "jin duo"})


def _norm(text: str | None) -> str:
    return " ".join((text or "").split()).casefold()


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == CHENG_RU_GROUP


class LotteryManager:
    """Runs lottery rounds over a fixed participant list while enforcing all rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._won_names: set[str] = set()
        self.results = ResultManager()
        self.last_two_draw_results: list[bool] = []
        self._rng = random.SystemRandom()

    # ----------------------------------------------------------- rule helpers
    def _is_won(self, user: User) -> bool:
        return _norm(user.name) in self._won_names

    def _fallback_active(self) -> bool:
        """True when the last two Chen Qixian / Jin Duo rounds both had no Cheng Ru members."""
        return len(self.last_two_draw_results) >= 2 and self.last_two_draw_results[-2:] == [False, False]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [u for u in self._users if not self._is_won(u)]
        drawer = _norm(prize.associated_drawer)

        # Cheng Ru group protection: overrides avoidance groups for Ma Jiaqi's prize.
        if drawer == MA_JIAQI and self._fallback_active():
            protected = [u for u in available if _is_cheng_ru(u)]
            if protected:
                return protected

        # Special rule: Li Bin's prizes only exclude previous winners.
        if drawer == LI_BIN:
            return available

        avoid = {_norm(group) for group in prize.avoid_groups}
        return [u for u in available if _norm(u.department) not in avoid]

    @staticmethod
    def describe_rule(prize: Prize) -> str:
        drawer = _norm(prize.associated_drawer)
        parts: list[str] = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        if drawer == LI_BIN:
            parts.append("Only previous winners are excluded (avoidance groups not applied)")
        else:
            parts.append("Previous winners are excluded")
            if prize.avoid_groups:
                parts.append("Avoidance group(s) excluded: " + ", ".join(prize.avoid_groups))
        if drawer == MA_JIAQI:
            parts.append(
                "Fallback: if the last two results of Chen Qixian and Jin Duo both lack "
                "Cheng Ru Group members, the pool is limited to Cheng Ru Group members"
            )
        return "; ".join(parts)

    # ----------------------------------------------------------------- draws
    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._won_names.add(_norm(user.name))
        self.results.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Record the round outcome so the fallback rule can be evaluated later."""
        if _norm(prize.associated_drawer) in FALLBACK_DRAWERS:
            has_cheng_ru = any(_is_cheng_ru(u) for u in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def draw_round(self, prize: Prize) -> list[User]:
        """Non-interactive convenience: draw all winners of a prize in one go."""
        winners: list[User] = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            winners.append(user)
        self.finish_round(prize, winners)
        return winners
