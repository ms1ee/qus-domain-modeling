"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

import random

from lottery_system.constants import (
    FALLBACK_DRAWER,
    PROTECTED_GROUP,
    SPECIAL_DRAWER,
    WATCHED_DRAWERS,
)
from lottery_system.models import Prize, User, normalize_text


def is_protected_group(department: str) -> bool:
    """True if the department is the protected 'Cheng Ru group'."""
    return normalize_text(department) == normalize_text(PROTECTED_GROUP)


class LotteryManager:
    """Runs individual draws while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        self._drawn: list[User] = []
        # Protection results (True = contained a Cheng Ru group member) of the most
        # recent draws made by the watched lottery persons (Chen Qixian, Jin Duo).
        self.last_two_draw_results: list[bool] = []

    @property
    def drawn_users(self) -> list[User]:
        """All users drawn so far, in draw order."""
        return list(self._drawn)

    def is_previous_winner(self, user: User) -> bool:
        """True if the user has already won in this lottery."""
        return normalize_text(user.name) in self._winner_names

    def _is_special_drawer(self, prize: Prize) -> bool:
        return normalize_text(prize.associated_drawer or "") == normalize_text(SPECIAL_DRAWER)

    def is_fallback_active(self, prize: Prize) -> bool:
        """Fallback applies when the drawer is Ma Jiaqi, the last two watched draws
        contained no protected members, and protected members remain available."""
        if normalize_text(prize.associated_drawer or "") != normalize_text(FALLBACK_DRAWER):
            return False
        if len(self.last_two_draw_results) != 2 or any(self.last_two_draw_results):
            return False
        return any(
            is_protected_group(u.department) and not self.is_previous_winner(u)
            for u in self._users
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return users eligible to win the given prize right now."""
        available = [u for u in self._users if not self.is_previous_winner(u)]

        # Special rule: Li Bin's prizes only filter previous winners.
        if self._is_special_drawer(prize):
            return available

        # Fallback rule: force the pool to the protected group, overriding avoidance.
        if self.is_fallback_active(prize):
            return [u for u in available if is_protected_group(u.department)]

        avoided = {normalize_text(group) for group in prize.avoid_groups}
        return [u for u in available if normalize_text(u.department) not in avoided]

    def draw_one(self, prize: Prize):
        """Draw a single winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        winner = random.choice(pool)
        self._winner_names.add(normalize_text(winner.name))
        self._drawn.append(winner)

        drawer = normalize_text(prize.associated_drawer or "")
        watched = {normalize_text(name) for name in WATCHED_DRAWERS}
        if drawer in watched:
            self.last_two_draw_results = (
                self.last_two_draw_results + [is_protected_group(winner.department)]
            )[-2:]
        elif drawer == normalize_text(FALLBACK_DRAWER):
            # Protection window consumed by Ma Jiaqi's draw.
            self.last_two_draw_results = []
        return winner

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        drawer = (prize.associated_drawer or "").strip()
        parts = ["previous winners are excluded"]
        if self._is_special_drawer(prize):
            parts.append(
                f"lottery person {SPECIAL_DRAWER}: avoidance groups do not apply"
            )
        elif self.is_fallback_active(prize):
            parts.append(
                f"{PROTECTED_GROUP} protection active: only its members are eligible"
            )
        elif prize.avoid_groups:
            parts.append("avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("no group avoidance")
        if drawer:
            parts.append(f"lottery person: {drawer}")
        return "; ".join(parts)
