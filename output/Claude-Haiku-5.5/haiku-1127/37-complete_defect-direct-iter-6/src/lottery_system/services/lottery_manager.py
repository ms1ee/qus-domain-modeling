"""Lottery rule engine: eligibility filtering, special rules, fallback protection and anti-duplication."""

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
    is_same_group,
    normalize_text,
)

FALLBACK_SOURCE_DRAWERS: tuple[str, str] = (CHEN_QIXIAN, JIN_DUO)
FALLBACK_TARGET_DRAWER: str = MA_JIAQI


class LotteryManager:
    """Runs lottery draws according to the rule engine."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self._rng = rng if rng is not None else random.Random()
        # Records whether the last two lottery persons' (Chen Qixian / Jin Duo) rounds
        # included a Cheng Ru Group member. True = protected group member won.
        self.last_two_draw_results: list[bool] = []

    # ------------------------------------------------------------------ helpers
    def has_won(self, user: User) -> bool:
        """Return True if the user has already won any prize."""
        return normalize_text(user.name) in self._winner_keys

    @staticmethod
    def _is_drawer(prize: Prize, drawer_name: str) -> bool:
        return prize.associated_drawer is not None and normalize_text(
            prize.associated_drawer
        ) == normalize_text(drawer_name)

    def _fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection applies to Ma Jiaqi when neither of the last two
        lottery persons' results contained a Cheng Ru Group member."""
        return (
            self._is_drawer(prize, FALLBACK_TARGET_DRAWER)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    # ------------------------------------------------------------------ rules
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the users eligible to win the given prize right now."""
        # Anti-duplication: previous winners are always excluded.
        pool = [user for user in self._users if not self.has_won(user)]

        # Special rule: Li Bin's prizes only filter previous winners.
        if self._is_drawer(prize, LI_BIN):
            return pool

        # Fallback (Cheng Ru group protection) overrides avoidance groups.
        if self._fallback_active(prize):
            return [user for user in pool if is_same_group(user.department, CHENG_RU_GROUP)]

        avoided = {normalize_text(group) for group in prize.avoid_groups}
        return [user for user in pool if normalize_text(user.department) not in avoided]

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        rules: list[str] = []
        if self._is_drawer(prize, LI_BIN):
            rules.append(
                "Special rule (Li Bin): only previous winners are excluded; "
                "group avoidance is not applied."
            )
        else:
            rules.append("Previous winners are excluded.")
            if self._fallback_active(prize):
                rules.append(
                    "Cheng Ru Group protection: candidates are limited to Cheng Ru Group members."
                )
            elif prize.avoid_groups:
                rules.append("Avoided groups: " + ", ".join(prize.avoid_groups) + ".")
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}.")
        return " ".join(rules)

    # ------------------------------------------------------------------ draws
    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(normalize_text(winner.name))
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback state after a round has completed (or was terminated)."""
        if self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            # The protected round has been handled; restart the observation window.
            self.last_two_draw_results = []
            return

        if any(self._is_drawer(prize, source) for source in FALLBACK_SOURCE_DRAWERS):
            has_cheng_ru = any(
                is_same_group(user.department, CHENG_RU_GROUP) for user in round_winners
            )
            self.last_two_draw_results = (self.last_two_draw_results + [has_cheng_ru])[-2:]
