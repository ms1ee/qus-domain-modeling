"""Lottery rule engine: eligibility pools, special rules and anti-duplication."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru Group"


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _is_cheng_ru_member(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Runs draws for prizes while enforcing the lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winners: list[User] = []
        self._won_names: set[str] = set()
        # Results of the most recent draws by Chen Qixian / Jin Duo:
        # True means the draw produced a Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        return list(self._winners)

    def has_won(self, user: User) -> bool:
        return _norm(user.name) in self._won_names

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the candidates for the next draw of the given prize.

        Priority:
        1. Previous winners are always excluded (anti-duplication).
        2. Fallback protection: if Ma Jiaqi is the lottery person and the last two
           results of Chen Qixian / Jin Duo contain no Cheng Ru group member, the
           pool is limited to Cheng Ru group members (ignoring avoidance groups).
        3. Special rule: Li Bin only filters previous winners.
        4. Otherwise members of avoidance groups are excluded in the first tier;
           they become eligible only after all other members are exhausted.
        """
        drawer = _norm(prize.associated_drawer)
        available = [user for user in self._users if not self.has_won(user)]

        if drawer == _norm(LI_BIN):
            return available

        if (
            drawer == _norm(MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        ):
            protected = [user for user in available if _is_cheng_ru_member(user)]
            if protected:
                return protected

        avoid = {_norm(group) for group in prize.avoid_groups}
        primary = [user for user in available if _norm(user.department) not in avoid]
        if primary:
            return primary
        return [user for user in available if _norm(user.department) in avoid]

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None when no candidate is eligible."""
        drawer = _norm(prize.associated_drawer)
        pool = self._get_eligible_pool(prize)
        winner = random.choice(pool) if pool else None

        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            self.last_two_draw_results = (
                self.last_two_draw_results
                + [winner is not None and _is_cheng_ru_member(winner)]
            )[-2:]
        elif drawer == _norm(MA_JIAQI):
            # Protection applies to the lottery person immediately following Chen/Jin.
            self.last_two_draw_results = []

        if winner is not None:
            self._winners.append(winner)
            self._won_names.add(_norm(winner.name))
        return winner
