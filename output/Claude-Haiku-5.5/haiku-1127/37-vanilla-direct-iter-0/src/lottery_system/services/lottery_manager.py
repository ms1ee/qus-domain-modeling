"""Lottery rule engine: eligibility filtering, drawing and fallback protection."""

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

PROTECTED_DRAWERS = (CHEN_QIXIAN, JIN_DUO)


def describe_rules(prize: Prize) -> str:
    """Human readable description of the rules applied to a prize round."""
    rules: list[str] = []
    drawer = prize.associated_drawer
    if drawer:
        rules.append(f"lottery person: {drawer}")
    rules.append("previous winners excluded")
    if drawer == LI_BIN:
        rules.append("special rule: avoidance groups NOT applied")
    elif prize.avoid_groups:
        rules.append("avoid groups: " + ", ".join(prize.avoid_groups))
    else:
        rules.append("no avoidance groups")
    if drawer == MA_JIAQI:
        rules.append(
            "Cheng Ru group protection: if the last two draws of Chen Qixian and "
            "Jin Duo contained no Cheng Ru group member, only Cheng Ru group "
            "members are eligible"
        )
    return "; ".join(rules)


class LotteryManager:
    """Performs draws while enforcing all lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self.users: list[User] = list(users)
        self._rng = rng if rng is not None else random.Random()
        self.winner_names: set[str] = set()
        # Results (True = Cheng Ru group member) of the most recent draws by
        # Chen Qixian / Jin Duo, keeping at most the last two.
        self.last_two_draw_results: list[bool] = []

    def _fallback_active(self) -> bool:
        """True when the last two protected draws contained no Cheng Ru group member."""
        return len(self.last_two_draw_results) == 2 and not any(
            self.last_two_draw_results
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the users eligible for the next pick of the given prize."""
        available = [user for user in self.users if user.name not in self.winner_names]
        drawer = prize.associated_drawer

        # Cheng Ru group protection overrides avoidance groups.
        if drawer == MA_JIAQI and self._fallback_active():
            protected = [user for user in available if user.department == CHENG_RU_GROUP]
            if protected:
                return protected

        # Special rule: Li Bin's prizes only filter previous winners.
        if drawer == LI_BIN:
            return available

        avoid = set(prize.avoid_groups)
        return [user for user in available if user.department not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible user exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        if prize.associated_drawer in PROTECTED_DRAWERS:
            self.last_two_draw_results.append(user.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return user

    def finish_round(self, prize: Prize) -> None:
        """Called when a round ends. Consumes the fallback protection after Ma Jiaqi's round."""
        if prize.associated_drawer == MA_JIAQI and self._fallback_active():
            self.last_two_draw_results = []
