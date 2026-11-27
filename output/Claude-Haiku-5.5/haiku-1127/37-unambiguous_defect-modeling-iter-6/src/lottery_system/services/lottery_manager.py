"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager, Winner

SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCH_DRAWERS: tuple[str, ...] = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"


def _same(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return a.strip().casefold() == b.strip().casefold()


def _key(name: str) -> str:
    return name.strip().casefold()


class LotteryManager:
    """Runs lottery draws for a list of users while enforcing all rules."""

    def __init__(self, users) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Results (True = contained Cheng Ru group member) of the most recent
        # draws by Chen Qixian / Jin Duo, oldest first, at most two entries.
        self.last_two_draw_results: list[bool] = []
        self._winner_keys: set[str] = set()
        self._rng = random.Random()

    # ----- winner bookkeeping -------------------------------------------------
    def is_winner(self, user: User) -> bool:
        return _key(user.name) in self._winner_keys

    def _available_users(self) -> list[User]:
        return [user for user in self.users if not self.is_winner(user)]

    # ----- fallback protection ------------------------------------------------
    def is_fallback_active(self) -> bool:
        """True when the last two Chen/Jin draws both had no Cheng Ru group member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _fallback_applies(self, prize: Prize) -> bool:
        return _same(prize.associated_drawer, FALLBACK_TARGET_DRAWER) and self.is_fallback_active()

    def _protected_pool(self) -> list[User]:
        return [
            user
            for user in self._available_users()
            if _same(user.department, PROTECTED_GROUP)
        ]

    # ----- rule engine --------------------------------------------------------
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self._available_users()

        # Special lottery person: relaxed rules (avoidance groups not applied).
        if _same(prize.associated_drawer, SPECIAL_DRAWER):
            return available

        # Fallback: Ma Jiaqi's prize is limited to Cheng Ru group members,
        # overriding avoidance groups.
        if self._fallback_applies(prize):
            protected = self._protected_pool()
            if protected:
                return protected

        # Basic filtering: exclude avoidance groups.
        avoid = prize.avoid_groups or []
        return [
            user
            for user in available
            if not any(_same(user.department, group) for group in avoid)
        ]

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        rules = ["previous winners are excluded"]
        if _same(prize.associated_drawer, SPECIAL_DRAWER):
            rules.append("relaxed rules for Li Bin: avoidance groups are not applied")
        elif self._fallback_applies(prize) and self._protected_pool():
            rules.append(
                "Cheng Ru group protection: only Cheng Ru Group members are eligible "
                "(avoidance groups overridden)"
            )
        elif prize.avoid_groups:
            rules.append("avoided groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(rules)

    # ----- drawing ------------------------------------------------------------
    def draw_next(self, prize: Prize) -> Winner | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        winner = self.result_manager.add_winner(user, prize)
        self._winner_keys.add(_key(user.name))
        return winner

    def record_round_result(self, prize: Prize, winners: list[Winner]) -> None:
        """Update fallback state after a lottery round finishes."""
        drawer = prize.associated_drawer
        if _same(drawer, FALLBACK_TARGET_DRAWER):
            # The protection has been consumed by this round; restart the sequence.
            self.last_two_draw_results = []
            return
        if any(_same(drawer, watched) for watched in FALLBACK_WATCH_DRAWERS):
            has_protected = any(
                _same(winner.user.department, PROTECTED_GROUP) for winner in winners
            )
            self.last_two_draw_results = (self.last_two_draw_results + [has_protected])[-2:]
