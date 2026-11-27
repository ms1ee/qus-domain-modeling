import random

from lottery_system.config import (
    CHENG_RU_GROUP,
    FALLBACK_DRAWERS,
    FALLBACK_TRIGGER_DRAWER,
    SPECIAL_NO_AVOID_DRAWER,
)
from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager


def _norm(text: str) -> str:
    return (text or "").strip().casefold()


class LotteryManager:
    """Executes lottery draws and applies the lottery rule engine."""

    def __init__(self, users, result_manager=None, rng=None):
        self.users: list[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        # Per-round results of Chen Qixian / Jin Duo: True if the round contained a Cheng Ru member.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    # ----- helpers -------------------------------------------------------

    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return _norm(user.department) == _norm(CHENG_RU_GROUP)

    def _fallback_active(self, prize: Prize) -> bool:
        """Fallback applies when Ma Jiaqi draws and the last two results of
        Chen Qixian / Jin Duo both contain no Cheng Ru group member."""
        if not self._is_drawer(prize, FALLBACK_TRIGGER_DRAWER):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results)

    # ----- rule engine ---------------------------------------------------

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        # Anti-duplication: previous winners are always excluded.
        pool = [user for user in self.users if not self.result_manager.has_won(user)]

        # Special rule: Li Bin's prizes only filter previous winners.
        if self._is_drawer(prize, SPECIAL_NO_AVOID_DRAWER):
            return pool

        # Fallback (Cheng Ru group protection): overrides avoidance groups.
        if self._fallback_active(prize):
            cheng_ru_pool = [user for user in pool if self._is_cheng_ru(user)]
            if cheng_ru_pool:
                return cheng_ru_pool

        # Basic rule: exclude avoidance groups of the prize.
        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in pool if _norm(user.department) not in avoid]

    def count_eligible(self, prize: Prize) -> int:
        return len(self._get_eligible_pool(prize))

    def describe_rules(self, prize: Prize) -> list[str]:
        rules: list[str] = []
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        rules.append("Previous winners are excluded.")
        if self._is_drawer(prize, SPECIAL_NO_AVOID_DRAWER):
            rules.append(f"Special rule for {SPECIAL_NO_AVOID_DRAWER}: avoidance groups are not applied.")
        elif prize.avoid_groups:
            rules.append("Avoidance groups excluded: " + ", ".join(prize.avoid_groups))
        if self._is_drawer(prize, FALLBACK_TRIGGER_DRAWER):
            rules.append(
                f"Fallback rule: if the last two results of {FALLBACK_DRAWERS[0]} and "
                f"{FALLBACK_DRAWERS[1]} contain no {CHENG_RU_GROUP} member, only "
                f"{CHENG_RU_GROUP} members are eligible."
            )
            if self._fallback_active(prize):
                rules.append("Fallback is ACTIVE for this round: only Cheng Ru group members are eligible.")
        return rules

    # ----- draw control --------------------------------------------------

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize, round_winners) -> None:
        """Update fallback state after a round has finished."""
        if self._is_drawer(prize, FALLBACK_TRIGGER_DRAWER):
            if self._fallback_active(prize):
                # The forced protection round has been consumed.
                self.last_two_draw_results.clear()
        elif any(self._is_drawer(prize, name) for name in FALLBACK_DRAWERS):
            self.last_two_draw_results.append(any(self._is_cheng_ru(user) for user in round_winners))
            del self.last_two_draw_results[:-2]
