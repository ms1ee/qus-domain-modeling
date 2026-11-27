"""Lottery rule engine: filtering, special rules, fallback and anti-duplication."""

from __future__ import annotations

import random

from ..models import Prize, User
from .result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru Group"
SPECIAL_DRAWER = "Li Bin"
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_DRAWERS = ("Chen Qixian", "Jin Duo")
HISTORY_LENGTH = 2


def _norm(text: str | None) -> str:
    return " ".join((text or "").split()).casefold()


def is_cheng_ru_member(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Draws winners for prizes while applying the lottery rules.

    last_two_draw_results: outcomes of the most recent individual draws made by
    Chen Qixian or Jin Duo (True if the drawn person is a Cheng Ru Group member).
    Ma Jiaqi's draws consume this history.
    """

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.result_manager = ResultManager()
        self.last_two_draw_results: list[bool] = []

    # ----- helpers -----
    @property
    def winners(self):
        return self.result_manager.get_all_winners()

    def _available_users(self) -> list[User]:
        return [u for u in self._users if _norm(u.name) not in self._winner_keys]

    @staticmethod
    def _drawer_key(prize: Prize) -> str:
        return _norm(prize.associated_drawer)

    def _fallback_pool(self, prize: Prize, available: list[User]) -> list[User] | None:
        """Cheng Ru group protection: returns the forced pool, or None if not active."""
        if self._drawer_key(prize) != _norm(FALLBACK_DRAWER):
            return None
        if len(self.last_two_draw_results) < HISTORY_LENGTH or any(self.last_two_draw_results):
            return None
        members = [u for u in available if is_cheng_ru_member(u)]
        return members or None

    def is_fallback_active(self, prize: Prize) -> bool:
        return self._fallback_pool(prize, self._available_users()) is not None

    # ----- rule engine -----
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self._available_users()

        fallback = self._fallback_pool(prize, available)
        if fallback is not None:
            return fallback

        if self._drawer_key(prize) == _norm(SPECIAL_DRAWER):
            # Relaxed rules for Li Bin: avoidance groups are not applied.
            return available

        avoid = {_norm(g) for g in prize.avoid_groups}
        return [u for u in available if _norm(u.department) not in avoid]

    def _record_draw(self, prize: Prize, user: User) -> None:
        self._winner_keys.add(_norm(user.name))
        self.result_manager.add_winner(user, prize)

        key = self._drawer_key(prize)
        if key in {_norm(d) for d in PROTECTED_DRAWERS}:
            self.last_two_draw_results.append(is_cheng_ru_member(user))
            del self.last_two_draw_results[:-HISTORY_LENGTH]
        elif key == _norm(FALLBACK_DRAWER):
            self.last_two_draw_results.clear()

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._record_draw(prize, user)
        return user

    def describe_rules(self, prize: Prize) -> str:
        key = self._drawer_key(prize)
        parts: list[str] = []
        if key == _norm(SPECIAL_DRAWER):
            parts.append(
                "Special rule for Li Bin: relaxed filtering, avoidance groups ignored; "
                "previous winners still excluded"
            )
        else:
            parts.append("Previous winners excluded")
            if prize.avoid_groups:
                parts.append("avoid groups: " + ", ".join(prize.avoid_groups))
            else:
                parts.append("no avoidance groups")
        if key == _norm(FALLBACK_DRAWER):
            parts.append(
                "Cheng Ru Group protection: if the last two draws by Chen Qixian/Jin Duo "
                "had no Cheng Ru Group winner, the pool is limited to Cheng Ru Group members"
            )
        if not prize.associated_drawer:
            parts.append("no specific lottery person")
        else:
            parts.append(f"lottery person: {prize.associated_drawer}")
        return "; ".join(parts)
