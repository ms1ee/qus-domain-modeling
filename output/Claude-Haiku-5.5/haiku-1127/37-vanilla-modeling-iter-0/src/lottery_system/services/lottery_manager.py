"""Lottery rule engine: eligibility filtering, special rules and fallback."""
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
    """Draws winners while enforcing the lottery rules."""

    def __init__(self, users):
        self.users: list[User] = list(users)
        self.winner_names: set[str] = set()
        # Outcomes (True = winner belongs to Cheng Ru group) of the most recent
        # draws by Chen Qixian / Jin Duo, keeping at most two entries.
        self.last_two_draw_results: list[bool] = []

    def is_winner(self, user: User) -> bool:
        return user.name in self.winner_names

    def is_fallback_active(self) -> bool:
        """Fallback triggers when the last two results both contain no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        pool = [u for u in self.users if u.name not in self.winner_names]
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            # Special rule: only previous winners are filtered.
            return pool
        if drawer == MA_JIAQI and self.is_fallback_active():
            # Fallback: force Cheng Ru group members, overriding avoidance groups.
            return [u for u in pool if u.department == CHENG_RU_GROUP]
        avoid = set(prize.avoid_groups)
        return [u for u in pool if u.department not in avoid]

    def get_eligible_count(self, prize: Prize) -> int:
        return len(self._get_eligible_pool(prize))

    def get_rule_description(self, prize: Prize) -> str:
        drawer = prize.associated_drawer
        if drawer == LI_BIN:
            return ("Previous winners are excluded; avoidance groups are NOT applied "
                    "(special rule for Li Bin).")
        if drawer == MA_JIAQI and self.is_fallback_active():
            return ("Fallback ACTIVE: only Cheng Ru group members are eligible "
                    "(previous winners excluded).")
        parts = ["Previous winners are excluded"]
        if prize.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if drawer == MA_JIAQI:
            parts.append("fallback: if the last two Chen Qixian/Jin Duo draws both had no "
                         "Cheng Ru group member, only Cheng Ru group members are eligible")
        return "; ".join(parts) + "."

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self.winner_names.add(winner.name)
        self._record_draw(prize, winner)
        return winner

    def _record_draw(self, prize: Prize, winner: User) -> None:
        if prize.associated_drawer in (CHEN_QIXIAN, JIN_DUO):
            self.last_two_draw_results.append(winner.department == CHENG_RU_GROUP)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def end_round(self, prize: Prize) -> None:
        """Called when a round finishes; resets the fallback state after Ma Jiaqi's round."""
        if prize.associated_drawer == MA_JIAQI:
            self.last_two_draw_results.clear()
