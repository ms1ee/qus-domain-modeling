"""Lottery rule engine: eligibility filtering, special rules, and draws."""

import random
from typing import Any

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    User,
)
from lottery_system.services.result_manager import ResultManager

# Lottery persons whose draw results feed the Cheng Ru group protection check.
_TRACKED_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
_PROTECTED_DRAWER = MA_JIAQI


def _same_text(a: str, b: str) -> bool:
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def _drawer_is(prize: Any, drawer: str) -> bool:
    return prize.associated_drawer is not None and _same_text(prize.associated_drawer, drawer)


class LotteryManager:
    """Runs individual draws while enforcing all lottery rules."""

    def __init__(
        self,
        users: list[User],
        result_manager: ResultManager | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.users: list[User] = list(users)
        self.result_manager: ResultManager = (
            result_manager if result_manager is not None else ResultManager()
        )
        # Whether the last (up to two) draws by Chen Qixian / Jin Duo contained
        # a Cheng Ru group member. True = protected member won.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()
        self._won_names: set[str] = set()

    # ------------------------------------------------------------------ rules
    @staticmethod
    def is_relaxed_prize(prize: Any) -> bool:
        """Special rule: prizes drawn by Li Bin use relaxed filtering."""
        return _drawer_is(prize, LI_BIN)

    def is_cheng_ru_protection_active(self, prize: Any) -> bool:
        """Fallback rule: Ma Jiaqi's pool is limited to Cheng Ru members when
        neither of the last two results of Chen Qixian / Jin Duo had a Cheng Ru member."""
        return (
            _drawer_is(prize, _PROTECTED_DRAWER)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def has_won(self, user: User) -> bool:
        """Anti-duplication check: whether this person already won any prize."""
        return user.name in self._won_names

    def _available_users(self) -> list[User]:
        return [user for user in self.users if not self.has_won(user)]

    def _get_eligible_pool(self, prize: Any) -> list[User]:
        """Compute the candidate pool for a prize."""
        available = self._available_users()

        if self.is_cheng_ru_protection_active(prize):
            protected = [u for u in available if _same_text(u.department, CHENG_RU_GROUP)]
            if protected:
                return protected
            # No protected member remains; fall back to the normal pool.

        if self.is_relaxed_prize(prize):
            return available

        avoid = {group.strip().casefold() for group in (prize.avoid_groups or [])}
        return [u for u in available if u.department.strip().casefold() not in avoid]

    def get_eligible_pool(self, prize: Any) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    # ------------------------------------------------------------------ draws
    def draw_once(self, prize: Any) -> User | None:
        """Draw one winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        user = self._rng.choice(pool)
        self._won_names.add(user.name)
        self.result_manager.add_winner(user, prize)

        drawer = prize.associated_drawer
        if drawer is not None and any(_same_text(drawer, d) for d in _TRACKED_DRAWERS):
            self._record_draw(_same_text(user.department, CHENG_RU_GROUP))
        return user

    def _record_draw(self, contains_cheng_ru: bool) -> None:
        self.last_two_draw_results = (self.last_two_draw_results + [contains_cheng_ru])[-2:]

    @property
    def winners(self) -> list:
        """All winners recorded so far, in winning order."""
        return self.result_manager.get_winners()
