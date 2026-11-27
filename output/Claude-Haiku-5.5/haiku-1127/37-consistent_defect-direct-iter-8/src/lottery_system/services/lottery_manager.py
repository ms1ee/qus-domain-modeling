"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    is_cheng_ru_department,
)


class LotteryManager:
    """Performs draws while enforcing all lottery rules.

    Rules:
    - Previous winners are never drawn again (for any prize).
    - Members of a prize's avoidance groups stay eligible, but are only drawn
      after all other eligible members have been drawn.
    - Lottery person Li Bin: only previous winners are filtered; avoidance groups are ignored.
    - Cheng Ru fallback: if the last two draws (by Chen Qixian / Jin Duo) both had no
      Cheng Ru Group winner, the next draw by Ma Jiaqi is limited to Cheng Ru Group members
      (even if that group is an avoidance group of the prize). The protection is reset after
      a Ma Jiaqi round.
    """

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winners: list[User] = []
        self._winner_keys: set[str] = set()
        self._round_winners: list[User] = []
        self._rng = rng or random.Random()
        # Each entry: whether a round of Chen Qixian / Jin Duo contained a Cheng Ru Group winner
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _key(user: User) -> str:
        return user.name.strip().casefold()

    @property
    def winners(self) -> list[User]:
        return list(self._winners)

    def is_winner(self, user: User) -> bool:
        return self._key(user) in self._winner_keys

    def _available_users(self) -> list[User]:
        return [user for user in self._users if not self.is_winner(user)]

    def is_cheng_ru_protection_active(self, prize: Prize) -> bool:
        """True if the Cheng Ru fallback forces this prize's pool."""
        return (
            prize.associated_drawer == MA_JIAQI
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the current candidate pool for the prize, in priority tier."""
        available = self._available_users()
        drawer = prize.associated_drawer

        # Special rule: Li Bin only filters previous winners.
        if drawer == LI_BIN:
            return available

        # Cheng Ru fallback: restrict to Cheng Ru Group members when protection is active.
        if self.is_cheng_ru_protection_active(prize):
            cheng_ru = [user for user in available if is_cheng_ru_department(user.department)]
            if cheng_ru:
                return cheng_ru

        avoid = {group.strip().casefold() for group in prize.avoid_groups}
        primary = [user for user in available if user.department.strip().casefold() not in avoid]
        if primary:
            return primary
        # Only avoidance-group members remain: they are drawn now, after everyone else.
        return [user for user in available if user.department.strip().casefold() in avoid]

    def start_round(self, prize: Prize) -> None:
        """Mark the beginning of a lottery round."""
        self._round_winners = []

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winners.append(user)
        self._winner_keys.add(self._key(user))
        self._round_winners.append(user)
        return user

    def end_round(self, prize: Prize) -> None:
        """Finish a round and update the fallback protection state."""
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN, JIN_DUO):
            has_cheng_ru = any(is_cheng_ru_department(u.department) for u in self._round_winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == MA_JIAQI:
            self.last_two_draw_results = []
        self._round_winners = []
