"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru group"
LI_BIN_NAME = "Li Bin"
CHEN_QIXIAN_NAME = "Chen Qixian"
JIN_DUO_NAME = "Jin Duo"
MA_JIAQI_NAME = "Ma Jiaqi"


class LotteryManager:
    """Runs individual draws while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Cheng Ru outcome (True = at least one Cheng Ru member won) of the
        # most recent draws made by Chen Qixian / Jin Duo (max two entries).
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()
        self._rng = random.Random()

    # ----- rule helpers -------------------------------------------------

    def _is_fallback_active(self, prize: Prize) -> bool:
        return (
            prize.associated_drawer == MA_JIAQI_NAME
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [u for u in self.users if u.name not in self._winner_names]

        # Special rule: Li Bin's rounds relax filtering (group avoidance ignored).
        if prize.associated_drawer == LI_BIN_NAME:
            return available

        # Fallback (Cheng Ru group protection): forced to Cheng Ru members,
        # even if Cheng Ru is an avoidance group of this prize.
        if self._is_fallback_active(prize):
            protected = [u for u in available if u.department == CHENG_RU_GROUP]
            if protected:
                return protected

        return [u for u in available if u.department not in prize.avoid_groups]

    def has_eligible(self, prize: Prize) -> bool:
        return len(self._get_eligible_pool(prize)) > 0

    def describe_rules(self, prize: Prize) -> str:
        rules = ["previous winners excluded"]
        drawer = prize.associated_drawer
        if drawer == LI_BIN_NAME:
            rules.append("special rule for Li Bin: group avoidance relaxed")
        elif prize.avoid_groups:
            rules.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if drawer == MA_JIAQI_NAME and self._is_fallback_active(prize):
            rules.append(
                "Cheng Ru group protection active: only Cheng Ru group members are eligible"
            )
        return "; ".join(rules)

    # ----- drawing ------------------------------------------------------

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)
        self._update_fallback_state(prize, user)
        return user

    def _update_fallback_state(self, prize: Prize, user: User) -> None:
        drawer = prize.associated_drawer
        if drawer in (CHEN_QIXIAN_NAME, JIN_DUO_NAME):
            self.last_two_draw_results.append(user.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def end_round(self, prize: Prize) -> None:
        """Must be called when a round finishes; resets fallback state after Ma Jiaqi's round."""
        if prize.associated_drawer == MA_JIAQI_NAME:
            self.last_two_draw_results = []
