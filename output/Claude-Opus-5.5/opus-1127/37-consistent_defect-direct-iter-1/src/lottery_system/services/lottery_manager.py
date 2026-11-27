"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User, normalize

CHENG_RU_GROUP = "Cheng Ru Group"
SPECIAL_DRAWER = "Li Bin"
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def is_cheng_ru(department: str) -> bool:
    key = (department or "").replace(" ", "").lower()
    return key in ("chengrugroup", "chengru")


class LotteryManager:
    """Applies the filtering rules and draws winners."""

    def __init__(self, users, rng=None) -> None:
        self.users: List[User] = list(users)
        self.winners: List[User] = []
        self._winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.SystemRandom()

    # ------------------------------------------------------------- rule helpers
    def is_winner(self, user: User) -> bool:
        return user.name in self._winner_names

    @staticmethod
    def _drawer(prize: Prize) -> str:
        return normalize(prize.associated_drawer)

    def is_special_drawer(self, prize: Prize) -> bool:
        return self._drawer(prize) == normalize(SPECIAL_DRAWER)

    def fallback_active(self, prize: Prize) -> bool:
        if self._drawer(prize) != normalize(FALLBACK_TARGET_DRAWER):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and not any(recent)

    def _not_won(self) -> List[User]:
        return [u for u in self.users if not self.is_winner(u)]

    def _is_avoided(self, user: User, prize: Prize) -> bool:
        avoid = {normalize(g) for g in prize.avoid_groups}
        return normalize(user.department) in avoid

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = self._not_won()
        if self.fallback_active(prize):
            forced = [u for u in candidates if is_cheng_ru(u.department)]
            if forced:
                return forced
        if self.is_special_drawer(prize):
            return candidates
        return [u for u in candidates if not self._is_avoided(u, prize)]

    def _get_secondary_pool(self, prize: Prize) -> List[User]:
        """Avoidance group members, drawn only after all other members."""
        if self.is_special_drawer(prize):
            return []
        if self.fallback_active(prize) and any(
            is_cheng_ru(u.department) for u in self._not_won()
        ):
            return []
        return [u for u in self._not_won() if self._is_avoided(u, prize)]

    # ------------------------------------------------------------------ drawing
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_secondary_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        if self.is_winner(user):  # anti-duplication safety net
            return None
        self.winners.append(user)
        self._winner_names.add(user.name)
        return user

    def draw_round(self, prize: Prize) -> List[User]:
        result = []
        for _ in range(prize.quantity):
            user = self.draw_one(prize)
            if user is None:
                break
            result.append(user)
        self.record_round_result(prize, result)
        return result

    def record_round_result(self, prize: Prize, round_winners) -> None:
        drawer = self._drawer(prize)
        if drawer in {normalize(d) for d in FALLBACK_TRIGGER_DRAWERS}:
            self.last_two_draw_results.append(
                any(is_cheng_ru(u.department) for u in round_winners)
            )
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer:
            self.last_two_draw_results = []

    def describe_rules(self, prize: Prize) -> List[str]:
        lines = []
        drawer = prize.associated_drawer or "(not specified)"
        lines.append(f"Lottery person: {drawer}")
        if self.fallback_active(prize):
            lines.append(
                f"Fallback rule: previous drawers ({', '.join(FALLBACK_TRIGGER_DRAWERS)}) "
                f"drew no '{CHENG_RU_GROUP}' members; pool is limited to '{CHENG_RU_GROUP}' members"
            )
        elif self.is_special_drawer(prize):
            lines.append(
                f"Special rule: drawer is {SPECIAL_DRAWER}, only previous winners are excluded "
                "(avoidance groups not applied)"
            )
        else:
            if prize.avoid_groups:
                lines.append(
                    "Avoidance groups: " + ", ".join(prize.avoid_groups)
                    + " (drawn only after all other members)"
                )
            else:
                lines.append("Avoidance groups: none")
        lines.append("Previous winners are excluded")
        return lines
