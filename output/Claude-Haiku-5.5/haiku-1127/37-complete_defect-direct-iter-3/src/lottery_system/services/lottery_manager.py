"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

import random

from lottery_system.models import Prize, User, normalize

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"
CHENG_RU_GROUP = "Cheng Ru Group"


class LotteryManager:
    """Runs lottery draws while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        # Results of the most recent rounds run by Chen Qixian / Jin Duo.
        # True means the round produced at least one Cheng Ru Group member.
        self.last_two_draw_results: list[bool] = []
        self._rng = random.Random()

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _key(user: User) -> str:
        return normalize(user.name)

    @staticmethod
    def _is_drawer(prize: Prize, drawer: str) -> bool:
        return prize.associated_drawer is not None and normalize(prize.associated_drawer) == normalize(drawer)

    def _is_li_bin(self, prize: Prize) -> bool:
        return self._is_drawer(prize, LI_BIN)

    def _is_ma_jiaqi(self, prize: Prize) -> bool:
        return self._is_drawer(prize, MA_JIAQI)

    def _is_chen_or_jin(self, prize: Prize) -> bool:
        return self._is_drawer(prize, CHEN_QIXIAN) or self._is_drawer(prize, JIN_DUO)

    @staticmethod
    def is_cheng_ru_member(user: User) -> bool:
        return normalize(user.department) == normalize(CHENG_RU_GROUP)

    def is_winner(self, user: User) -> bool:
        return self._key(user) in self._winner_keys

    def is_forced_cheng_ru(self, prize: Prize) -> bool:
        """Fallback protection: Ma Jiaqi's prize is limited to Cheng Ru Group when
        the last two Chen Qixian / Jin Duo rounds both had no Cheng Ru Group winner."""
        return (
            self._is_ma_jiaqi(prize)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _apply_avoid_groups(self, pool: list[User], prize: Prize) -> list[User]:
        if not prize.avoid_groups or self._is_li_bin(prize):
            # Special rule: Li Bin's prizes only filter previous winners.
            return list(pool)
        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in pool if normalize(u.department) not in avoid]

    # ----- rule engine ---------------------------------------------------
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may win the given prize right now."""
        available = [u for u in self.users if not self.is_winner(u)]

        if self.is_forced_cheng_ru(prize):
            forced = [u for u in available if self.is_cheng_ru_member(u)]
            if forced:
                # Forced limit ignores avoidance groups (including Cheng Ru Group
                # being an avoidance group of this prize).
                return forced
            # No Cheng Ru Group member left: fall back to the normal pool.

        return self._apply_avoid_groups(available, prize)

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts = ["Previous winners are excluded"]
        if self._is_li_bin(prize):
            if prize.avoid_groups:
                parts.append("special drawer Li Bin: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if self.is_forced_cheng_ru(prize):
            parts.append("Cheng Ru Group protection active: only Cheng Ru Group members are eligible")
        return "; ".join(parts)

    # ----- drawing -------------------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(self._key(winner))
        return winner

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback-protection state after a round has finished.

        Rounds without any winners (e.g. skipped) do not change the state.
        """
        if not winners:
            return
        if self._is_chen_or_jin(prize):
            has_cheng_ru = any(self.is_cheng_ru_member(u) for u in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._is_ma_jiaqi(prize):
            # The protection has been applied; start a fresh observation window.
            self.last_two_draw_results = []
