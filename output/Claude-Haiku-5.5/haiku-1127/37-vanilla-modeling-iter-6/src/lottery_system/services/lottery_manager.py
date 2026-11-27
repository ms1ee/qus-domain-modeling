"""Lottery rule engine: eligibility filtering, drawing and fallback protection."""

import random

from lottery_system.config import (
    CHENG_RU_GROUP,
    CHEN_QIXIAN,
    FALLBACK_TARGET_DRAWER,
    FALLBACK_TRIGGER_DRAWERS,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


def _norm(text: str | None) -> str:
    return " ".join((text or "").split()).casefold()


class LotteryManager:
    """Performs lottery rounds while enforcing all eligibility rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_keys: set[str] = set()
        # Records whether each recent draw by Chen Qixian / Jin Duo contained
        # Cheng Ru group members (True) or not (False). Keeps last two entries.
        self.last_two_draw_results: list[bool] = []
        self._round_hits: list[User] = []

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return _norm(user.department) == _norm(CHENG_RU_GROUP)

    def _is_previous_winner(self, user: User) -> bool:
        return _norm(user.name) in self._winner_keys

    @staticmethod
    def _is_li_bin(prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == _norm(LI_BIN)

    @staticmethod
    def _is_ma_jiaqi(prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == _norm(FALLBACK_TARGET_DRAWER)

    def _is_fallback_active(self, prize: Prize) -> bool:
        if not self._is_ma_jiaqi(prize):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) == 2 and recent == [False, False]

    # ----- eligibility ---------------------------------------------------
    def _eligible_pool(self, prize: Prize) -> list[User]:
        pool = [u for u in self._users if not self._is_previous_winner(u)]
        if self._is_li_bin(prize):
            # Special rule: only previous winners are filtered.
            return pool
        if self._is_fallback_active(prize):
            # Fallback: only Cheng Ru group members, overriding avoidance groups.
            return [u for u in pool if self._is_cheng_ru(u)]
        avoid = {_norm(group) for group in prize.avoid_groups}
        return [u for u in pool if _norm(u.department) not in avoid]

    def pool_size(self, prize: Prize) -> int:
        return len(self._eligible_pool(prize))

    def describe_rule(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if self._is_li_bin(prize):
            parts.append("Special rule for Li Bin: avoidance groups are not applied")
        elif prize.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        if self._is_ma_jiaqi(prize):
            if self._is_fallback_active(prize):
                parts.append(
                    f"Fallback active: only {CHENG_RU_GROUP} members are eligible"
                )
            else:
                parts.append(
                    f"Fallback applies if {CHEN_QIXIAN} and {JIN_DUO} both missed "
                    f"{CHENG_RU_GROUP} members"
                )
        return "; ".join(parts)

    # ----- drawing -------------------------------------------------------
    def start_round(self, prize: Prize) -> None:
        self._round_hits = []

    def draw_one(self, prize: Prize) -> User | None:
        pool = self._eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winners.append(user)
        self._winner_keys.add(_norm(user.name))
        self._round_hits.append(user)
        return user

    def end_round(self, prize: Prize) -> list[User]:
        hits = list(self._round_hits)
        drawer = _norm(prize.associated_drawer)
        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            self.last_two_draw_results.append(any(self._is_cheng_ru(u) for u in hits))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(MA_JIAQI):
            # The fallback check for this consecutive sequence is consumed.
            self.last_two_draw_results = []
        self._round_hits = []
        return hits
