"""Lottery rule engine: eligibility pool, drawing and fallback protection."""

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
    """Runs lottery rounds while enforcing all eligibility rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        # Results of the last two draws by Chen Qixian / Jin Duo:
        # True if that draw produced a Cheng Ru Group member.
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()
        self._round_prize: Prize | None = None
        self._round_winners: list[User] = []

    # ------------------------------------------------------------------ #
    # Rule helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_cheng_ru_member(user: User) -> bool:
        return user.department == CHENG_RU_GROUP

    def is_fallback_active(self) -> bool:
        """True when neither of the last two Chen/Jin draws had Cheng Ru members."""
        return len(self.last_two_draw_results) >= 2 and not any(
            self.last_two_draw_results[-2:]
        )

    def _available_users(self) -> list[User]:
        """Users who have not won yet (anti-duplication)."""
        return [user for user in self.users if user.name not in self._winner_names]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        pool = self._available_users()

        # Special rule: Li Bin only filters previous winners.
        if prize.associated_drawer == LI_BIN:
            return pool

        # Fallback (Cheng Ru group protection) for Ma Jiaqi's prize pool.
        if prize.associated_drawer == MA_JIAQI and self.is_fallback_active():
            return [user for user in pool if self.is_cheng_ru_member(user)]

        avoid = set(prize.avoid_groups or [])
        return [user for user in pool if user.department not in avoid]

    # ------------------------------------------------------------------ #
    # Round control
    # ------------------------------------------------------------------ #
    def start_round(self, prize: Prize) -> None:
        self._round_prize = prize
        self._round_winners = []

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if pool is empty."""
        if self._round_prize is None or self._round_prize.name != prize.name:
            self.start_round(prize)
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winner_names.add(user.name)
        self._round_winners.append(user)
        return user

    def end_round(self) -> None:
        """Finish the current round and update fallback tracking."""
        prize = self._round_prize
        if prize is None:
            return
        if prize.associated_drawer in (CHEN_QIXIAN, JIN_DUO):
            produced_cheng_ru = any(
                self.is_cheng_ru_member(user) for user in self._round_winners
            )
            self.last_two_draw_results.append(produced_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        self._round_prize = None
        self._round_winners = []
