"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

import random

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_KEYWORD,
    FALLBACK_CONSECUTIVE_DRAWS,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User, normalize_text

MONITORED_DRAWERS = frozenset({normalize_text(CHEN_QIXIAN), normalize_text(JIN_DUO)})
FALLBACK_DRAWER = normalize_text(MA_JIAQI)
RELAXED_DRAWER = normalize_text(LI_BIN)


def is_cheng_ru_member(user: User) -> bool:
    return CHENG_RU_KEYWORD in normalize_text(user.department)


class LotteryManager:
    def __init__(self, users, rng=None):
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self._rng = rng if rng is not None else random.Random()
        # Results of the most recent draws by Chen Qixian / Jin Duo:
        # True if that draw produced a Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    def is_winner(self, user: User) -> bool:
        return normalize_text(user.name) in self._winner_keys

    def _fallback_active(self) -> bool:
        return (
            len(self.last_two_draw_results) == FALLBACK_CONSECUTIVE_DRAWS
            and not any(self.last_two_draw_results)
        )

    def is_fallback_active_for(self, prize: Prize) -> bool:
        drawer = normalize_text(prize.associated_drawer or "")
        return drawer == FALLBACK_DRAWER and self._fallback_active()

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [u for u in self._users if not self.is_winner(u)]
        drawer = normalize_text(prize.associated_drawer or "")

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members,
        # even if that group is an avoidance group of the prize.
        if drawer == FALLBACK_DRAWER and self._fallback_active():
            return [u for u in available if is_cheng_ru_member(u)]

        # Special rule: Li Bin's draws use relaxed filtering (avoidance groups ignored).
        if drawer == RELAXED_DRAWER:
            return available

        avoid = {normalize_text(group) for group in prize.avoid_groups}
        return [u for u in available if normalize_text(u.department) not in avoid]

    def draw_next(self, prize: Prize) -> User | None:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(normalize_text(winner.name))
        return winner

    def end_round(self, prize: Prize, round_winners) -> None:
        drawer = normalize_text(prize.associated_drawer or "")
        if drawer == FALLBACK_DRAWER:
            # The fallback check has been consumed by this round.
            self.last_two_draw_results.clear()
        elif drawer in MONITORED_DRAWERS:
            hit = any(is_cheng_ru_member(w) for w in round_winners)
            self.last_two_draw_results.append(hit)
            del self.last_two_draw_results[:-FALLBACK_CONSECUTIVE_DRAWS]
