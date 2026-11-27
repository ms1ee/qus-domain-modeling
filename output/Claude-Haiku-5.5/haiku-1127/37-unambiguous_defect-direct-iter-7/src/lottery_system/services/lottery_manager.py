"""Lottery rule engine: filtering, special rules, fallback and anti-duplication."""

from __future__ import annotations

import random

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
)
from lottery_system.models import Prize, User


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Executes lottery rounds while enforcing the lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        self.drawn_names: set[str] = set()
        # Cheng Ru group presence of the last two draws by Chen Qixian / Jin Duo.
        # True means the round produced at least one Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []
        self._round_winners: list[User] = []

    # ------------------------------------------------------------------
    # Rule engine
    # ------------------------------------------------------------------
    def is_cheng_ru_protection_active(self, prize: Prize) -> bool:
        """Fallback rule: Ma Jiaqi's pool is limited to Cheng Ru group members
        when the last two consecutive draws (Chen Qixian, Jin Duo) both
        contained no Cheng Ru group members."""
        return (
            _norm(prize.associated_drawer) == _norm(MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users eligible to win the given prize right now."""
        # Anti-duplication: previous winners (any prize) are always excluded.
        candidates = [user for user in self.users if user.name not in self.drawn_names]

        # Cheng Ru group protection (overrides avoidance groups).
        if self.is_cheng_ru_protection_active(prize):
            protected = [user for user in candidates if _is_cheng_ru(user)]
            if protected:
                return protected

        # Special rule: relaxed filtering for Li Bin.
        if _norm(prize.associated_drawer) == _norm(LI_BIN):
            return candidates

        # Basic filtering: exclude members of avoidance groups.
        avoid = {_norm(group) for group in prize.avoid_groups}
        return [user for user in candidates if _norm(user.department) not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the current eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts = ["Previous winners are excluded"]
        if _norm(prize.associated_drawer) == _norm(LI_BIN):
            parts.append("Relaxed rule for Li Bin: group avoidance is not applied")
        elif prize.avoid_groups:
            parts.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        if self.is_cheng_ru_protection_active(prize):
            parts.append(
                "Cheng Ru Group protection ACTIVE: only Cheng Ru Group members are eligible"
            )
        return "; ".join(parts)

    # ------------------------------------------------------------------
    # Round execution
    # ------------------------------------------------------------------
    def start_round(self, prize: Prize) -> None:
        """Begin a new round for the given prize."""
        self._round_winners = []

    def draw_next(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no candidate exists."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self.drawn_names.add(winner.name)
        self._round_winners.append(winner)
        return winner

    def end_round(self, prize: Prize) -> list[User]:
        """Finish the round, update fallback history and return round winners."""
        winners = list(self._round_winners)
        drawer = _norm(prize.associated_drawer)
        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            had_cheng_ru = any(_is_cheng_ru(user) for user in winners)
            self.last_two_draw_results = (self.last_two_draw_results + [had_cheng_ru])[-2:]
        self._round_winners = []
        return winners
