"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)


class LotteryManager:
    """Performs individual draws while enforcing all lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self._winners: list[User] = []
        self._rng = rng if rng is not None else random.Random()
        # Results (True = contained a Cheng Ru Group member) of the most recent
        # draws by Chen Qixian / Jin Duo, at most the last two entries.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        """All winners drawn so far, in winning order."""
        return list(self._winners)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return user.department.strip().lower() == CHENG_RU_GROUP.lower()

    def is_fallback_active(self) -> bool:
        """True when the last two Chen/Jin draws both had no Cheng Ru Group winner."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the candidates eligible for the next draw of `prize`."""
        # Basic filter: exclude all previous winners (anti-duplication).
        available = [user for user in self._users if user.name not in self._winner_names]
        drawer = (prize.associated_drawer or "").strip()

        # Fallback (Cheng Ru Group protection): forced pool, overrides avoid groups.
        if drawer == MA_JIAQI and self.is_fallback_active():
            return [user for user in available if self._is_cheng_ru(user)]

        # Special rule for Li Bin: relaxed filtering, avoid groups are not applied.
        if drawer == LI_BIN:
            return available

        # Basic filter: exclude members of the prize's avoidance groups.
        avoid = {group.strip().lower() for group in prize.avoid_groups}
        return [user for user in available if user.department.strip().lower() not in avoid]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for `prize`. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        self._winners.append(winner)
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback state after a prize round has finished."""
        drawer = (prize.associated_drawer or "").strip()
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            hit = any(self._is_cheng_ru(user) for user in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI:
            # The Ma Jiaqi round consumes the fallback state.
            self.last_two_draw_results = []
