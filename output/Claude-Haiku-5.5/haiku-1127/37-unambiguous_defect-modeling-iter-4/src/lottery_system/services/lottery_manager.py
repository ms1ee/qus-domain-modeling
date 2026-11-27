"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

CHENG_RU_KEYWORD = "cheng ru"
PROTECTED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
RELAXED_DRAWER = "Li Bin"


def is_cheng_ru(department: str) -> bool:
    """Return True if the department belongs to the Cheng Ru group."""
    return CHENG_RU_KEYWORD in department.strip().lower()


class LotteryManager:
    """Runs lottery draws while enforcing the lottery rules.

    Rules:
    - Previous winners are never drawn again.
    - Members of the prize's avoidance groups are excluded (basic rule).
    - Drawer "Li Bin" uses relaxed filtering (avoidance groups ignored).
    - Cheng Ru fallback: if the last two draws by Chen Qixian / Jin Duo contained
      no Cheng Ru member, the next draw by Ma Jiaqi is limited to Cheng Ru members
      (overriding avoidance groups). After Ma Jiaqi draws, the window is reset.
    """

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.winner_names: set[str] = set()
        self.last_two_draw_results: list[bool] = []

    def is_fallback_active(self) -> bool:
        """Return True when the Cheng Ru protection must apply to Ma Jiaqi's draw."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users eligible to win the given prize right now."""
        pool = [user for user in self.users if user.name not in self.winner_names]
        drawer = prize.associated_drawer

        if drawer == FALLBACK_TARGET_DRAWER and self.is_fallback_active():
            return [user for user in pool if is_cheng_ru(user.department)]

        if drawer == RELAXED_DRAWER:
            return pool

        avoided = {group.strip().lower() for group in prize.avoid_groups}
        return [user for user in pool if user.department.strip().lower() not in avoided]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None

        winner = random.choice(pool)
        self.winner_names.add(winner.name)

        drawer = prize.associated_drawer
        if drawer in PROTECTED_DRAWERS:
            self._record_draw(is_cheng_ru(winner.department))
        elif drawer == FALLBACK_TARGET_DRAWER:
            self.last_two_draw_results.clear()
        return winner

    def _record_draw(self, contains_cheng_ru: bool) -> None:
        """Keep only the results of the last two protected draws."""
        self.last_two_draw_results = (self.last_two_draw_results + [contains_cheng_ru])[-2:]

    def describe_rule(self, prize: Prize) -> str:
        """Return a human readable description of the rules applied to the prize."""
        parts: list[str] = ["Previous winners excluded"]
        drawer = prize.associated_drawer

        if drawer == RELAXED_DRAWER:
            parts.append("Special rule (Li Bin): avoidance groups relaxed")
        elif drawer == FALLBACK_TARGET_DRAWER and self.is_fallback_active():
            parts.append(
                "Cheng Ru group protection active: only Cheng Ru Group members eligible "
                "(avoidance groups overridden)"
            )
        elif prize.avoid_groups:
            parts.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")

        if drawer:
            parts.append(f"Drawer: {drawer}")
        return "; ".join(parts)
