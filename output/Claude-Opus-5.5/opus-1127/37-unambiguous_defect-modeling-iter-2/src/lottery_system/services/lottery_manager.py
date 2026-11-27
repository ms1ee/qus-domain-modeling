"""Lottery rule engine and drawing logic."""

from __future__ import annotations

import random
from typing import List, Optional, Set

from lottery_system.models import Prize, User, normalize_group

RELAXED_DRAWER = "Li Bin"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _same_person(a: Optional[str], b: str) -> bool:
    return a is not None and " ".join(a.split()).lower() == b.lower()


class LotteryManager:
    """Applies filtering rules, the fallback mechanism and anti-duplication."""

    def __init__(self, users, rng: Optional[random.Random] = None) -> None:
        self.users: List[User] = list(users or [])
        self.winner_names: Set[str] = set()
        self.last_two_draw_results: List[bool] = []
        self.fallback_triggered: bool = False
        self._rng = rng or random.SystemRandom()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _key(user: User) -> str:
        return user.name.strip().lower()

    def has_won(self, user: User) -> bool:
        return self._key(user) in self.winner_names

    def mark_winner(self, user: User) -> bool:
        key = self._key(user)
        if key in self.winner_names:
            return False
        self.winner_names.add(key)
        return True

    @staticmethod
    def is_protected_member(user: User) -> bool:
        return normalize_group(user.department) == normalize_group(PROTECTED_GROUP)

    def is_fallback_active(self, prize: Prize) -> bool:
        if not _same_person(prize.associated_drawer, FALLBACK_TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    # ---------------------------------------------------------------- rule core
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        not_won = [u for u in self.users if not self.has_won(u)]

        if self.is_fallback_active(prize):
            protected = [u for u in not_won if self.is_protected_member(u)]
            if protected:
                self.fallback_triggered = True
                return protected
            # No protected member available: fall through to normal rules.

        if _same_person(prize.associated_drawer, RELAXED_DRAWER):
            # Relaxed rules: avoidance groups are not applied,
            # only previous winners are excluded.
            return not_won

        avoid = {normalize_group(g) for g in prize.avoid_groups}
        return [u for u in not_won if normalize_group(u.department) not in avoid]

    def get_rule_description(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if self.is_fallback_active(prize):
            parts.append(f"FALLBACK ACTIVE: pool limited to '{PROTECTED_GROUP}' members "
                         f"(overrides avoidance groups)")
        elif _same_person(drawer, RELAXED_DRAWER):
            parts.append(f"Relaxed rules for lottery person {RELAXED_DRAWER}: avoidance groups ignored")
        if prize.avoid_groups and not _same_person(drawer, RELAXED_DRAWER):
            parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
        elif not prize.avoid_groups:
            parts.append("No avoidance groups")
        parts.append(f"Lottery person: {drawer or 'None'}")
        return "; ".join(parts)

    # ------------------------------------------------------------------ drawing
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self.mark_winner(winner)
        return winner

    def draw(self, prize: Prize, count: Optional[int] = None) -> List[User]:
        count = prize.quantity if count is None else count
        winners: List[User] = []
        for _ in range(count):
            w = self.draw_one(prize)
            if w is None:
                break
            winners.append(w)
        self.record_round_result(prize, winners)
        return winners

    def record_round_result(self, prize: Prize, winners: List[User]) -> None:
        """Update fallback monitoring state after a round has finished."""
        drawer = prize.associated_drawer
        if any(_same_person(drawer, m) for m in MONITORED_DRAWERS):
            self.last_two_draw_results.append(any(self.is_protected_member(w) for w in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            # Consecutiveness broken or fallback consumed by the target drawer.
            self.last_two_draw_results = []
