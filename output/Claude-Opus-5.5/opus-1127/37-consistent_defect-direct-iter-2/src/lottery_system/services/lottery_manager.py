"""Lottery rule engine."""

import random
from typing import List, Optional

from lottery_system.models import Prize, User

LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru Group"


def _norm(text) -> str:
    return "".join(str(text or "").lower().split())


def is_cheng_ru(user: User) -> bool:
    return _norm(user.department) in ("chengrugroup", "chengru")


class LotteryManager:
    """Applies lottery rules and draws winners."""

    def __init__(self, users, rng=None) -> None:
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[tuple] = []
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.SystemRandom()

    # ----------------------------------------------------------------- helpers
    def is_winner(self, user: User) -> bool:
        return user.name in self.winner_names

    @staticmethod
    def _is_drawer(prize: Prize, name: str) -> bool:
        return _norm(prize.associated_drawer) == _norm(name)

    def is_fallback_active(self, prize: Prize) -> bool:
        return (self._is_drawer(prize, MA_JIAQI)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    # -------------------------------------------------------------------- pool
    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if not self.is_winner(u)]
        if self.is_fallback_active(prize):
            cheng_ru = [u for u in candidates if is_cheng_ru(u)]
            if cheng_ru:
                return cheng_ru
        if self._is_drawer(prize, LI_BIN):
            return candidates
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        if not avoid:
            return candidates
        primary = [u for u in candidates if _norm(u.department) not in avoid]
        if primary:
            return primary
        # Avoidance group members remain eligible, but are drawn after others.
        return [u for u in candidates if _norm(u.department) in avoid]

    # ------------------------------------------------------------------- draw
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winner_names.add(user.name)
        self.winners.append((user, prize))
        return user

    def record_round(self, prize: Prize, round_winners) -> None:
        if self._is_drawer(prize, CHEN_QIXIAN) or self._is_drawer(prize, JIN_DUO):
            self.last_two_draw_results.append(any(is_cheng_ru(u) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []

    def describe_rules(self, prize: Prize) -> str:
        lines = [f"Lottery person: {prize.associated_drawer or 'Not specified'}"]
        if self.is_fallback_active(prize):
            lines.append("Fallback (Cheng Ru group protection) ACTIVE: prize pool is "
                         "limited to Cheng Ru group members")
        elif self._is_drawer(prize, LI_BIN):
            lines.append("Special rule (Li Bin): only previous winners are excluded; "
                         "avoidance groups are not applied")
        elif prize.avoid_groups:
            lines.append("Previous winners excluded; members of avoidance groups ("
                         + ", ".join(prize.avoid_groups)
                         + ") are drawn only after all other members")
        else:
            lines.append("Previous winners excluded; no avoidance groups")
        return "\n".join(lines)
