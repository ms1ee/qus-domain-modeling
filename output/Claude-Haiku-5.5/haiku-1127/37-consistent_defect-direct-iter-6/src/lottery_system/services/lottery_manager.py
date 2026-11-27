"""Lottery rule engine: eligibility filtering and drawing."""

from __future__ import annotations

import random
from collections.abc import Iterable

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


class LotteryManager:
    """Runs individual draws while enforcing the lottery rules."""

    def __init__(self, users: Iterable[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._rng = rng if rng is not None else random.Random()
        self._winner_names: set[str] = set()
        # Cheng Ru group flags of the most recent draws by Chen Qixian / Jin Duo.
        # True means the winner belonged to the Cheng Ru group.
        self.last_two_draw_results: list[bool] = []

    @property
    def users(self) -> list[User]:
        return list(self._users)

    def mark_as_winner(self, user: User) -> None:
        """Record a person as already having won (e.g. from earlier rounds)."""
        self._winner_names.add(user.name)

    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    def _candidates(self) -> list[User]:
        """All participants who have not won yet."""
        return [u for u in self._users if u.name not in self._winner_names]

    def _cheng_ru_protection_active(self) -> bool:
        """True when the last two Chen/Jin draws both had no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the pool the next winner of this prize is drawn from.

        - Previous winners are always excluded.
        - Cheng Ru protection (Ma Jiaqi): if protection is active, the pool is
          limited to Cheng Ru group members, even if that group is an avoidance group.
        - Li Bin: only previous winners are filtered; avoidance groups are not applied.
        - Otherwise, members of avoidance groups stay eligible but are only drawn
          after all other members are exhausted.
        """
        candidates = self._candidates()
        if not candidates:
            return []

        drawer = prize.associated_drawer
        if drawer == MA_JIAQI and self._cheng_ru_protection_active():
            forced = [u for u in candidates if u.department == CHENG_RU_GROUP]
            if forced:
                return forced

        if drawer == LI_BIN:
            return candidates

        avoid = set(prize.avoid_groups)
        primary = [u for u in candidates if u.department not in avoid]
        if primary:
            return primary
        return candidates

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        self._update_protection_state(prize, winner)
        return winner

    def _update_protection_state(self, prize: Prize, winner: User) -> None:
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            self.last_two_draw_results.append(winner.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI:
            # The Ma Jiaqi round consumes the protection window.
            self.last_two_draw_results = []
