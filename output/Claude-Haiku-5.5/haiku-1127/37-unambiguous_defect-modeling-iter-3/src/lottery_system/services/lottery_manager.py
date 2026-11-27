"""Lottery rule engine: eligibility filtering, special rules and fallback."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User

PROTECTED_GROUP = "Cheng Ru group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winner_names: set[str] = set()
        # Results (True = contained a Cheng Ru group member) of the most recent
        # draws made by Chen Qixian / Jin Duo, at most two entries.
        self.last_two_draw_results: list[bool] = []

    # ----- rule helpers -------------------------------------------------
    @staticmethod
    def is_protected(user: User) -> bool:
        return _norm(user.department) == _norm(PROTECTED_GROUP)

    def is_fallback_active(self) -> bool:
        """True when the last two Chen/Jin draws both had no Cheng Ru member."""
        return len(self.last_two_draw_results) == 2 and not any(
            self.last_two_draw_results
        )

    def _available_users(self) -> list[User]:
        """Users who have not won yet (anti-duplication)."""
        return [u for u in self.users if u.name not in self.winner_names]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self._available_users()
        drawer = _norm(prize.associated_drawer)

        # Fallback (Cheng Ru group protection): forced pool for Ma Jiaqi.
        if drawer == _norm(MA_JIAQI) and self.is_fallback_active():
            forced = [u for u in available if self.is_protected(u)]
            if forced:
                return forced

        # Special rule: Li Bin's prizes use relaxed filtering (no group avoidance).
        if drawer == _norm(LI_BIN):
            return available

        # Basic filtering: exclude the prize's avoidance groups.
        avoided = {_norm(group) for group in prize.avoid_groups}
        return [u for u in available if _norm(u.department) not in avoided]

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        rules = ["previous winners excluded"]
        drawer = _norm(prize.associated_drawer)
        if drawer == _norm(LI_BIN):
            rules.append("relaxed filtering for Li Bin (group avoidance not applied)")
        elif prize.avoid_groups:
            rules.append("avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("no group avoidance")
        if drawer == _norm(MA_JIAQI):
            if self.is_fallback_active():
                rules.append(
                    f"{PROTECTED_GROUP} protection ACTIVE: pool limited to its members"
                )
            else:
                rules.append(
                    f"{PROTECTED_GROUP} protection armed (triggers if the last two "
                    f"Chen Qixian/Jin Duo draws had no {PROTECTED_GROUP} winner)"
                )
        return "; ".join(rules)

    # ----- drawing ------------------------------------------------------
    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        winner: User | None = None
        if pool:
            winner = random.choice(pool)
            self.winner_names.add(winner.name)

        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(name) for name in FALLBACK_TRIGGER_DRAWERS}:
            contains_protected = winner is not None and self.is_protected(winner)
            self.last_two_draw_results.append(contains_protected)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner
