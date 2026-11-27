"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.config import (
    CHENG_RU_GROUP,
    DRAWER_CHEN_QIXIAN,
    DRAWER_JIN_DUO,
    DRAWER_LI_BIN,
    DRAWER_MA_JIAQI,
    FALLBACK_WINDOW_SIZE,
)
from lottery_system.models import Prize, User

MONITORED_DRAWERS = (DRAWER_CHEN_QIXIAN, DRAWER_JIN_DUO)


class LotteryManager:
    """Runs draws for prizes while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_names: set[str] = set()
        # Cheng Ru membership results (True = winner belongs to Cheng Ru Group)
        # of the most recent draws by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self.consecutive_non_cheng_ru_count: int = 0
        self.fallback_active: bool = False

    def is_fallback_active(self) -> bool:
        """True when the last two monitored draws contained no Cheng Ru Group member."""
        window = self.last_two_draw_results[-FALLBACK_WINDOW_SIZE:]
        return len(window) >= FALLBACK_WINDOW_SIZE and not any(window)

    def _refresh_state(self) -> None:
        count = 0
        for result in reversed(self.last_two_draw_results):
            if result:
                break
            count += 1
        self.consecutive_non_cheng_ru_count = count
        self.fallback_active = self.is_fallback_active()

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute users eligible for the next draw of the given prize."""
        pool = [u for u in self.users if u.name not in self._winner_names]
        drawer = prize.associated_drawer

        # Special rule: Li Bin's draws use relaxed filtering (avoidance groups ignored).
        if drawer == DRAWER_LI_BIN:
            return pool

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru Group members, overriding avoidance.
        if drawer == DRAWER_MA_JIAQI and self.is_fallback_active():
            protected = [u for u in pool if u.department == CHENG_RU_GROUP]
            if protected:
                return protected

        # Basic filtering: exclude avoidance groups.
        return [u for u in pool if u.department not in prize.avoid_groups]

    def eligible_count(self, prize: Prize) -> int:
        """Number of users currently eligible for the prize."""
        return len(self._get_eligible_pool(prize))

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible participant remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._record_draw(winner, prize)
        return winner

    def _record_draw(self, user: User, prize: Prize) -> None:
        self._winner_names.add(user.name)
        self.winners.append(user)
        drawer = prize.associated_drawer
        if drawer in MONITORED_DRAWERS:
            self.last_two_draw_results.append(user.department == CHENG_RU_GROUP)
            del self.last_two_draw_results[:-FALLBACK_WINDOW_SIZE]
        elif drawer == DRAWER_MA_JIAQI:
            # Ma Jiaqi's turn closes the current monitoring cycle.
            self.last_two_draw_results.clear()
        self._refresh_state()


def describe_prize_rule(prize: Prize) -> str:
    """Human-readable description of the rules applied to a prize."""
    drawer = prize.associated_drawer
    parts: list[str] = []
    if drawer:
        parts.append(f"Lottery person: {drawer}.")
    else:
        parts.append("No lottery person assigned.")

    if drawer == DRAWER_LI_BIN:
        parts.append("Relaxed rules: previous winners excluded, avoidance groups ignored.")
    else:
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
        parts.append(f"Previous winners excluded; avoidance groups: {groups}.")

    if drawer == DRAWER_MA_JIAQI:
        parts.append(
            f"Fallback: if the last two draws by {DRAWER_CHEN_QIXIAN} and {DRAWER_JIN_DUO} "
            f"had no {CHENG_RU_GROUP} member, only {CHENG_RU_GROUP} members may win."
        )
    return " ".join(parts)
