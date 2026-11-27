"""Lottery rule engine: eligibility filtering, drawing and fallback protection."""

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
FALLBACK_DRAWERS = (CHEN_QIXIAN, JIN_DUO)


class LotteryManager:
    """Runs lottery draws while applying all rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results (True = contained a Cheng Ru group member) of the most recent
        # rounds run by Chen Qixian / Jin Duo, newest last. Max length 2.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    def _unrestricted_pool(self) -> list[User]:
        """Everyone who has not won yet."""
        winners = self.result_manager.winner_names()
        return [user for user in self.users if user.name not in winners]

    def _fallback_active(self) -> bool:
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _cheng_ru_fallback_pool(self, prize: Prize, pool: list[User]) -> list[User] | None:
        """Cheng Ru group protection pool for Ma Jiaqi's prizes, or None if not applicable."""
        if prize.associated_drawer != MA_JIAQI or not self._fallback_active():
            return None
        members = [user for user in pool if user.department == CHENG_RU_GROUP]
        return members or None

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        pool = self._unrestricted_pool()

        # Special rule: Li Bin only filters previous winners.
        if prize.associated_drawer == LI_BIN:
            return pool

        # Fallback rule: forcibly limit to Cheng Ru group members, overriding avoidance.
        fallback = self._cheng_ru_fallback_pool(prize, pool)
        if fallback is not None:
            return fallback

        if prize.avoid_groups:
            avoided = set(prize.avoid_groups)
            pool = [user for user in pool if user.department not in avoided]
        return pool

    def has_candidates(self, prize: Prize) -> bool:
        """Whether at least one person is eligible for the prize right now."""
        return bool(self._get_eligible_pool(prize))

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one eligible winner and record them. Returns None if no candidates."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self.result_manager.add_winner(winner, prize)
        return winner

    def record_round_result(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback state after a round. Only Chen Qixian / Jin Duo rounds count."""
        if prize.associated_drawer not in FALLBACK_DRAWERS:
            return
        contains_cheng_ru = any(user.department == CHENG_RU_GROUP for user in winners)
        self.last_two_draw_results = (self.last_two_draw_results + [contains_cheng_ru])[-2:]

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize."""
        parts: list[str] = []
        if prize.associated_drawer:
            parts.append(f"lottery person: {prize.associated_drawer}")
        if prize.associated_drawer == LI_BIN:
            parts.append("only previous winners are excluded (avoidance groups not applied)")
        elif self._cheng_ru_fallback_pool(prize, self._unrestricted_pool()) is not None:
            parts.append(
                f"Cheng Ru group protection active: only '{CHENG_RU_GROUP}' members are eligible"
            )
        else:
            parts.append("previous winners are excluded")
            if prize.avoid_groups:
                parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(parts)
