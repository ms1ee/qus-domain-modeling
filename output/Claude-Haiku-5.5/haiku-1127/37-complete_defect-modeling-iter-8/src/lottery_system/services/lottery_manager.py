from __future__ import annotations

import random

from lottery_system.models import Prize, User


CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def _same(a: str | None, b: str | None) -> bool:
    return _norm(a) == _norm(b) and _norm(a) != ""


class LotteryManager:
    """Executes lottery rounds and enforces the lottery rule engine."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._rng = rng if rng is not None else random.Random()
        self._winners: list[User] = []
        self._winner_keys: set[str] = set()
        # Rolling record (max 2 entries) of whether the last rounds run by
        # Chen Qixian / Jin Duo contained a Cheng Ru Group member.
        self.last_two_draw_results: list[bool] = []
        self._round_prize: Prize | None = None
        self._round_winners: list[User] = []
        self._round_quota: int = 0

    # ------------------------------------------------------------------ state
    @property
    def winners(self) -> list[User]:
        return list(self._winners)

    @property
    def is_round_active(self) -> bool:
        return self._round_prize is not None

    def _is_winner(self, user: User) -> bool:
        return _norm(user.name) in self._winner_keys

    def _is_fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru protection: applies to Ma Jiaqi's prize when the last two
        Chen Qixian / Jin Duo rounds contained no Cheng Ru Group member."""
        if not _same(prize.associated_drawer, MA_JIAQI):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results)

    # ------------------------------------------------------------ rule engine
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        candidates = [user for user in self._users if not self._is_winner(user)]

        # Special rule: Li Bin's prize only excludes previous winners.
        if _same(prize.associated_drawer, LI_BIN):
            return candidates

        # Fallback rule: pool forcibly limited to Cheng Ru Group members,
        # even if that group is an avoidance group of this prize.
        if self._is_fallback_active(prize):
            return [u for u in candidates if _same(u.department, CHENG_RU_GROUP)]

        avoid = {_norm(group) for group in prize.avoid_groups}
        return [u for u in candidates if _norm(u.department) not in avoid]

    def describe_rule(self, prize: Prize) -> str:
        parts: list[str] = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        if _same(prize.associated_drawer, LI_BIN):
            parts.append(
                "Special rule: only previous winners are excluded; avoidance groups do not apply"
            )
        elif self._is_fallback_active(prize):
            parts.append("Fallback rule active: only Cheng Ru Group members are eligible")
        elif prize.avoid_groups:
            parts.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No group avoidance")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)

    # ---------------------------------------------------------- round control
    def start_round(self, prize: Prize) -> None:
        if self._round_prize is not None:
            raise RuntimeError("A lottery round is already in progress.")
        self._round_prize = prize
        self._round_winners = []
        self._round_quota = prize.quantity

    def draw_next(self) -> User | None:
        """Draw the next winner of the active round. Returns None if no draw is possible."""
        if self._round_prize is None:
            raise RuntimeError("No lottery round is in progress.")
        if len(self._round_winners) >= self._round_quota:
            return None
        pool = self._get_eligible_pool(self._round_prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._round_winners.append(user)
        self._winners.append(user)
        self._winner_keys.add(_norm(user.name))
        return user

    def end_round(self) -> list[User]:
        """Close the active round, update fallback records and return its winners."""
        prize = self._round_prize
        winners = list(self._round_winners)
        if prize is None:
            return []

        drawer = prize.associated_drawer
        if _same(drawer, CHEN_QIXIAN) or _same(drawer, JIN_DUO):
            has_cheng_ru = any(_same(u.department, CHENG_RU_GROUP) for u in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif _same(drawer, MA_JIAQI):
            # Ma Jiaqi's round consumes the consecutive-miss window.
            self.last_two_draw_results = []

        self._round_prize = None
        self._round_winners = []
        self._round_quota = 0
        return winners

    def draw(self, prize: Prize) -> list[User]:
        """Convenience: run a full round without interaction."""
        self.start_round(prize)
        while self.draw_next() is not None:
            pass
        return self.end_round()
