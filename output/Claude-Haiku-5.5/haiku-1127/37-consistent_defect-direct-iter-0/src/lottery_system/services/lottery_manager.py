"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

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
    normalize,
    same_text,
)
from lottery_system.services.result_manager import ResultManager, Winner


class LotteryManager:
    """Runs lottery draws for a fixed participant list while applying all rules.

    Rules:
    - Previous winners are never drawn again (regardless of prize type).
    - Members of a prize's avoid groups stay eligible but are drawn only
      after all other eligible members.
    - Lottery person "Li Bin": only previous winners are excluded; avoid
      groups are not applied.
    - Cheng Ru fallback: if the last two draws made by Chen Qixian / Jin Duo
      contained no Cheng Ru Group member, the next round drawn by Ma Jiaqi
      is limited to Cheng Ru Group members.
    """

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Cheng Ru membership flags of the most recent draws by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._winner_keys: set[str] = set()
        self._forced_round: str | None = None
        self._rng = random.SystemRandom()

    # ----- helpers -------------------------------------------------------

    @staticmethod
    def _user_key(user: User) -> str:
        return normalize(user.name)

    def is_winner(self, user: User) -> bool:
        return self._user_key(user) in self._winner_keys

    @staticmethod
    def _is_li_bin(prize: Prize) -> bool:
        return same_text(prize.associated_drawer or "", LI_BIN)

    @staticmethod
    def _is_ma_jiaqi(prize: Prize) -> bool:
        return same_text(prize.associated_drawer or "", MA_JIAQI)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return same_text(user.department, CHENG_RU_GROUP)

    def _is_avoided(self, user: User, prize: Prize) -> bool:
        if self._is_li_bin(prize):
            return False
        return any(same_text(user.department, group) for group in prize.avoid_groups)

    def _fallback_active(self, prize: Prize) -> bool:
        """True if the Cheng Ru fallback limits this prize's pool."""
        if not self._is_ma_jiaqi(prize):
            return False
        if self._forced_round == prize.name:
            return True
        return len(self.last_two_draw_results) == 2 and not any(
            self.last_two_draw_results
        )

    # ----- round control -------------------------------------------------

    def start_round(self, prize: Prize) -> None:
        """Prepare a new round; decides whether the fallback applies to it."""
        self._forced_round = None
        if self._is_ma_jiaqi(prize) and self._fallback_active(prize):
            self._forced_round = prize.name
            # The protection is consumed by this round.
            self.last_two_draw_results = []

    def describe_rule(self, prize: Prize) -> str:
        """Human readable description of the rules applied to a prize round."""
        if self._is_li_bin(prize):
            return (
                "Only previous winners are excluded; avoid groups are not applied "
                "(lottery person: Li Bin)."
            )
        if self._fallback_active(prize):
            return (
                "Cheng Ru fallback active: only "
                f"{CHENG_RU_GROUP} members are eligible in this round."
            )
        parts = ["Previous winners are excluded."]
        if prize.avoid_groups:
            parts.append(
                "Members of avoid groups ("
                + ", ".join(prize.avoid_groups)
                + ") are drawn after other members."
            )
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}.")
        return " ".join(parts)

    # ----- eligibility and drawing --------------------------------------

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return all eligible users for a prize.

        Non-avoided members come first, followed by avoided members (who
        remain eligible but are drawn last).
        """
        available = [u for u in self.users if not self.is_winner(u)]

        if self._is_li_bin(prize):
            return available

        if self._fallback_active(prize):
            return [u for u in available if self._is_cheng_ru(u)]

        normal = [u for u in available if not self._is_avoided(u, prize)]
        avoided = [u for u in available if self._is_avoided(u, prize)]
        return normal + avoided

    def draw_one(self, prize: Prize) -> Winner | None:
        """Draw one winner for a prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        preferred = [u for u in pool if not self._is_avoided(u, prize)]
        candidates = preferred or pool
        user = self._rng.choice(candidates)

        winner = self.result_manager.add_winner(user, prize)
        self._winner_keys.add(self._user_key(user))
        self._record_draw_result(prize, user)
        return winner

    def _record_draw_result(self, prize: Prize, user: User) -> None:
        drawer = normalize(prize.associated_drawer or "")
        if drawer in (normalize(CHEN_QIXIAN), normalize(JIN_DUO)):
            self.last_two_draw_results.append(self._is_cheng_ru(user))
            del self.last_two_draw_results[:-2]
