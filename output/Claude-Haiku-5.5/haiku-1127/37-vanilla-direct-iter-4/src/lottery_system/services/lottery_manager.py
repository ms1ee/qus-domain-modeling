"""Lottery rule engine and draw execution."""

import random

from lottery_system.config import (
    CHENG_RU_GROUP,
    DRAWER_CHEN_QIXIAN,
    DRAWER_JIN_DUO,
    DRAWER_LI_BIN,
    DRAWER_MA_JIAQI,
)
from lottery_system.models import Prize, User, normalize
from lottery_system.services.result_manager import ResultManager


def is_cheng_ru_member(user: User) -> bool:
    """Return True if the user belongs to the Cheng Ru group."""
    return normalize(user.department) == normalize(CHENG_RU_GROUP)


class LotteryManager:
    """Executes lottery rounds while enforcing all eligibility rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self._round_winners: list[User] = []
        # Results of the last draws by Chen Qixian / Jin Duo: True if the round
        # contained at least one Cheng Ru group member. Keeps at most two entries.
        self.last_two_draw_results: list[bool] = []
        self.result_manager = ResultManager()

    # ----- rule helpers -------------------------------------------------

    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return prize.associated_drawer is not None and normalize(prize.associated_drawer) == normalize(
            drawer_name
        )

    def _fallback_active(self) -> bool:
        """Cheng Ru protection applies when the last two draw results both lack Cheng Ru members."""
        return len(self.last_two_draw_results) >= 2 and self.last_two_draw_results[-2:] == [False, False]

    def _available_users(self) -> list[User]:
        return [user for user in self._users if normalize(user.name) not in self._winner_keys]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users eligible to win the given prize in the current state."""
        available = self._available_users()

        # Special rule: Li Bin's prizes only filter previous winners.
        if self._is_drawer(prize, DRAWER_LI_BIN):
            return available

        # Fallback rule: Ma Jiaqi's prize is restricted to Cheng Ru group members,
        # overriding avoidance groups.
        if self._is_drawer(prize, DRAWER_MA_JIAQI) and self._fallback_active():
            return [user for user in available if is_cheng_ru_member(user)]

        # Basic rule: exclude previous winners and avoidance groups.
        avoided = {normalize(group) for group in prize.avoid_groups}
        return [user for user in available if normalize(user.department) not in avoided]

    def eligible_candidates(self, prize: Prize) -> list[User]:
        """Public accessor for the current eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def describe_rule(self, prize: Prize) -> str:
        """Return a human-readable description of the rules applied to a prize."""
        if self._is_drawer(prize, DRAWER_LI_BIN):
            return (
                "Only previous winners are excluded (special rule for Li Bin: "
                "avoidance groups are not applied)."
            )
        if self._is_drawer(prize, DRAWER_MA_JIAQI) and self._fallback_active():
            return (
                f"{CHENG_RU_GROUP} protection active: only {CHENG_RU_GROUP} members are eligible "
                "(avoidance groups overridden)."
            )
        parts = ["Previous winners are excluded"]
        if prize.avoid_groups:
            parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(parts) + "."

    # ----- round execution ----------------------------------------------

    def start_round(self, prize: Prize) -> None:
        """Begin a round for the given prize."""
        self._round_winners = []

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winner_keys.add(normalize(user.name))
        self._round_winners.append(user)
        self.result_manager.add_winner(user, prize)
        return user

    def finish_round(self, prize: Prize) -> list[User]:
        """Finish the round, update fallback history, and return the round winners."""
        winners = list(self._round_winners)
        if self._is_drawer(prize, DRAWER_CHEN_QIXIAN) or self._is_drawer(prize, DRAWER_JIN_DUO):
            contains_cheng_ru = any(is_cheng_ru_member(user) for user in winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._is_drawer(prize, DRAWER_MA_JIAQI):
            # Protection (if any) has been applied; reset the history.
            self.last_two_draw_results = []
        self._round_winners = []
        return winners
