"""Lottery rule engine."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager, Winner

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"
LOTTERY_PERSONS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

CHENG_RU_KEYWORD = "cheng ru"


def _norm(text) -> str:
    return " ".join(str(text).split()).casefold()


def is_cheng_ru_group(department: str) -> bool:
    """True if the department is the Cheng Ru group."""
    return CHENG_RU_KEYWORD in _norm(department)


class LotteryManager:
    """Applies the lottery rules and tracks winners and fallback history."""

    def __init__(self, users) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results of the last two rounds drawn by Chen Qixian / Jin Duo.
        # True means that round produced a Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        self._round_prize: Prize | None = None
        self._round_cheng_ru_hit = False

    # ----- helpers -----

    def _drawer_is(self, prize: Prize, drawer: str) -> bool:
        return _norm(prize.associated_drawer or "") == _norm(drawer)

    def _is_special_person(self, prize: Prize) -> bool:
        return self._drawer_is(prize, LI_BIN)

    def _is_protection_active(self, prize: Prize) -> bool:
        return (
            self._drawer_is(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _is_avoided(self, user: User, prize: Prize) -> bool:
        avoid = {_norm(group) for group in prize.avoid_groups}
        return _norm(user.department) in avoid

    def _candidates(self) -> list[User]:
        winner_names = {w.user.name for w in self.result_manager.winners}
        return [u for u in self.users if u.name not in winner_names]

    def _build_pool(self, prize: Prize) -> tuple[list[User], bool]:
        """Return (pool, flat). flat=True means no avoidance tiering applies."""
        candidates = self._candidates()

        if self._is_protection_active(prize):
            protected = [u for u in candidates if is_cheng_ru_group(u.department)]
            if protected:
                return protected, True

        if self._is_special_person(prize):
            return candidates, True

        primary = [u for u in candidates if not self._is_avoided(u, prize)]
        secondary = [u for u in candidates if self._is_avoided(u, prize)]
        return primary + secondary, False

    # ----- public API -----

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Eligible participants for the prize.

        - Previous winners are always excluded.
        - Li Bin special rule: only previous winners are excluded.
        - Cheng Ru protection: when active, pool is limited to Cheng Ru members.
        - Otherwise avoidance-group members remain eligible but are placed
          after all other members.
        """
        pool, _ = self._build_pool(prize)
        return pool

    def draw_next(self, prize: Prize) -> Winner | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        pool, flat = self._build_pool(prize)
        if not pool:
            return None

        if flat:
            choices = pool
        else:
            primary = [u for u in pool if not self._is_avoided(u, prize)]
            choices = primary or pool

        user = random.choice(choices)
        winner = self.result_manager.add_winner(user, prize)

        drawer_triggers = self._drawer_is(prize, CHEN_QIXIAN) or self._drawer_is(
            prize, JIN_DUO
        )
        if drawer_triggers and is_cheng_ru_group(user.department):
            self._round_cheng_ru_hit = True
        return winner

    def start_round(self, prize: Prize) -> None:
        self._round_prize = prize
        self._round_cheng_ru_hit = False

    def end_round(self, prize: Prize) -> None:
        """Finish a round and record its result for the fallback rule."""
        if self._drawer_is(prize, CHEN_QIXIAN) or self._drawer_is(prize, JIN_DUO):
            self.last_two_draw_results.append(self._round_cheng_ru_hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        self._round_prize = None
        self._round_cheng_ru_hit = False

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable rule description for a prize round."""
        rules: list[str] = []
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}.")

        if self._is_special_person(prize):
            rules.append(
                "Only previous winners are excluded; avoidance groups do not apply."
            )
        else:
            rules.append("Previous winners are excluded.")
            if prize.avoid_groups:
                rules.append(
                    "Members of avoidance group(s) "
                    f"{', '.join(prize.avoid_groups)} are drawn after all other members."
                )
            if self._drawer_is(prize, MA_JIAQI):
                rules.append(
                    "Cheng Ru Group protection: if neither of the last two Chen Qixian/"
                    "Jin Duo rounds produced a Cheng Ru Group winner, the pool is "
                    "limited to Cheng Ru Group members."
                )
                if self._is_protection_active(prize):
                    rules.append("Cheng Ru Group protection is ACTIVE for this round.")
        return " ".join(rules)
