"""Lottery execution and rule engine."""

from __future__ import annotations

import random
from typing import Callable

from lottery_system.models import (
    LI_BIN,
    MA_JIAQI,
    PROTECTION_DRAWERS,
    Prize,
    User,
    is_cheng_ru,
)
from lottery_system.services.result_manager import ResultManager


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


class LotteryManager:
    """Runs lottery rounds while applying the lottery rule engine."""

    def __init__(self, users: list[User], result_manager: ResultManager | None = None) -> None:
        self.users: list[User] = list(users)
        self.result_manager: ResultManager = (
            result_manager if result_manager is not None else ResultManager()
        )
        # Results of the most recent rounds run by Chen Qixian / Jin Duo.
        # True means that round produced at least one Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        # Anti-duplication: names of everyone who has already won.
        self._winner_names: set[str] = {
            winner.user.name for winner in self.result_manager.get_all_winners()
        }

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def get_winner_names(self) -> set[str]:
        return set(self._winner_names)

    def run_round(
        self,
        prize: Prize,
        on_winner: Callable[[int, int, User], None] | None = None,
        before_draw: Callable[[int, int], bool] | None = None,
    ) -> list[User]:
        """Run one lottery round for ``prize``.

        ``before_draw(index, total)`` is called before each draw; returning
        False ends the round early (used for the 'terminate' command).
        ``on_winner(index, total, user)`` is called after each successful draw.
        """
        winners: list[User] = []
        total = prize.quantity
        for index in range(1, total + 1):
            pool = self._get_eligible_pool(prize)
            if not pool:
                break
            if before_draw is not None and not before_draw(index, total):
                break
            chosen = random.choice(pool)
            self._record_winner(chosen, prize)
            winners.append(chosen)
            if on_winner is not None:
                on_winner(index, total, chosen)
        self._update_draw_history(prize, winners)
        return winners

    # ------------------------------------------------------------------
    # Rule engine
    # ------------------------------------------------------------------
    def _available_users(self) -> list[User]:
        return [user for user in self.users if user.name not in self._winner_names]

    def _protection_active(self) -> bool:
        """Cheng Ru protection triggers when the last two results both lack Cheng Ru winners."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self._available_users()
        drawer = _norm(prize.associated_drawer)

        # Fallback mechanism: Cheng Ru group protection for Ma Jiaqi's prize.
        if drawer == _norm(MA_JIAQI) and self._protection_active():
            protected = [user for user in available if is_cheng_ru(user)]
            if protected:
                return protected
            # No Cheng Ru members left: fall back to the normal rules.

        # Special rule: relaxed filtering for Li Bin (avoidance groups ignored).
        if drawer == _norm(LI_BIN):
            return available

        # Basic filtering: exclude members of the prize's avoidance groups.
        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in available if _norm(user.department) not in avoid]

    def _record_winner(self, user: User, prize: Prize) -> None:
        self._winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)

    def _update_draw_history(self, prize: Prize, winners: list[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer == _norm(MA_JIAQI):
            # Protection has been applied/consumed; reset the history.
            self.last_two_draw_results.clear()
            return
        protection_drawers = {_norm(name) for name in PROTECTION_DRAWERS}
        if drawer in protection_drawers and winners:
            has_cheng_ru = any(is_cheng_ru(user) for user in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            del self.last_two_draw_results[:-2]
