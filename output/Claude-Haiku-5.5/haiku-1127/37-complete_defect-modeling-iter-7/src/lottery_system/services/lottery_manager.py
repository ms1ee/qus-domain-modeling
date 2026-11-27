"""Lottery rule engine: eligibility pool, drawing and fallback protection."""

from __future__ import annotations

import random

from ..config import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from ..models import Prize, User


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


class LotteryManager:
    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self.users: list[User] = list(users)
        self.winners: list[User] = []
        self._winner_keys: set[str] = set()
        # Results of the most recent consecutive Chen Qixian / Jin Duo rounds:
        # True means that round produced at most one Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    def has_won(self, user: User) -> bool:
        return _norm(user.name) in self._winner_keys

    def is_fallback_active(self, prize: Prize) -> bool:
        """Cheng Ru fallback applies to Ma Jiaqi when neither of the last two
        Chen Qixian / Jin Duo results contained a Cheng Ru group member."""
        return (
            _norm(prize.associated_drawer) == _norm(MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [user for user in self.users if not self.has_won(user)]
        drawer = _norm(prize.associated_drawer)

        # Fallback mechanism: forcibly limit to Cheng Ru group members,
        # overriding the prize's avoidance groups.
        if drawer == _norm(MA_JIAQI) and self.is_fallback_active(prize):
            return [u for u in available if _norm(u.department) == _norm(CHENG_RU_GROUP)]

        # Special rule: Li Bin's prizes only exclude previous winners.
        if drawer == _norm(LI_BIN) or not prize.avoid_groups:
            return available

        avoided = {_norm(group) for group in prize.avoid_groups}
        return [user for user in available if _norm(user.department) not in avoided]

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one eligible winner at random; returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self.winners.append(winner)
        self._winner_keys.add(_norm(winner.name))
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Update fallback state once a round ends."""
        drawer = _norm(prize.associated_drawer)
        if drawer in (_norm(CHEN_QIXIAN), _norm(JIN_DUO)):
            contains_protected = any(
                _norm(user.department) == _norm(CHENG_RU_GROUP) for user in round_winners
            )
            self.last_two_draw_results = (self.last_two_draw_results + [contains_protected])[-2:]
        elif drawer == _norm(MA_JIAQI):
            self.last_two_draw_results = []

    def describe_rules(self, prize: Prize) -> str:
        drawer = _norm(prize.associated_drawer)
        rules = ["previous winners are excluded"]
        if drawer == _norm(LI_BIN):
            rules.append("special rule for Li Bin: avoidance groups are not applied")
        elif drawer == _norm(MA_JIAQI) and self.is_fallback_active(prize):
            rules.append("fallback protection active: only Cheng Ru Group members "
                         "are eligible (avoidance groups overridden)")
        else:
            if prize.avoid_groups:
                rules.append("avoided groups: " + ", ".join(prize.avoid_groups))
            if drawer == _norm(MA_JIAQI):
                rules.append("fallback protection inactive")
        return "; ".join(rules)
