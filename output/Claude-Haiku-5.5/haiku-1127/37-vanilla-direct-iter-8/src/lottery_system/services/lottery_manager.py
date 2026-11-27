"""Lottery rule engine: eligibility filtering, special rules and fallback."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize,
)

_HISTORY_DRAWERS = {normalize(CHEN_QIXIAN), normalize(JIN_DUO)}
_FALLBACK_TARGET = normalize(MA_JIAQI)
_SPECIAL_NO_AVOID = normalize(LI_BIN)
_CHENG_RU_KEY = normalize(CHENG_RU_GROUP)


class LotteryManager:
    """Runs lottery rounds for a fixed list of participants."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self._round_prize: Prize | None = None
        self._round_winners: list[User] = []
        # Round results (True = the round contained Cheng Ru Group members)
        # for the most recent rounds drawn by Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _name_key(user: User) -> str:
        return normalize(user.name)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize(user.department) == _CHENG_RU_KEY

    @staticmethod
    def _drawer_key(prize: Prize) -> str:
        return normalize(prize.associated_drawer) if prize.associated_drawer else ""

    def is_winner(self, user: User) -> bool:
        """Return True if the user has already won a prize."""
        return self._name_key(user) in self._winner_keys

    def is_cheng_ru_protection_active(self) -> bool:
        """True when the last two Chen/Jin rounds both had no Cheng Ru members."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may win the given prize right now."""
        available = [user for user in self._users if not self.is_winner(user)]
        drawer = self._drawer_key(prize)

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru Group members,
        # overriding avoidance groups.
        if drawer == _FALLBACK_TARGET and self.is_cheng_ru_protection_active():
            return [user for user in available if self._is_cheng_ru(user)]

        # Special rule: Li Bin only filters previous winners.
        if drawer == _SPECIAL_NO_AVOID:
            return available

        avoid = {normalize(group) for group in prize.avoid_groups}
        return [user for user in available if normalize(user.department) not in avoid]

    def has_candidates(self, prize: Prize) -> bool:
        """Return True if at least one eligible candidate remains for the prize."""
        return bool(self._get_eligible_pool(prize))

    def describe_rules(self, prize: Prize) -> str:
        """Return a human-readable description of the rules for a prize round."""
        rules = ["Previous winners are excluded."]
        drawer = self._drawer_key(prize)
        if drawer == _SPECIAL_NO_AVOID:
            rules.append("Special rule for Li Bin: avoidance groups do not apply.")
        elif drawer == _FALLBACK_TARGET and self.is_cheng_ru_protection_active():
            rules.append(
                "Cheng Ru Group protection is active: only Cheng Ru Group members "
                "are eligible (avoidance groups overridden)."
            )
        elif prize.avoid_groups:
            rules.append("Avoidance groups excluded: " + ", ".join(prize.avoid_groups) + ".")
        else:
            rules.append("No avoidance groups.")
        if prize.associated_drawer:
            rules.append(f"Associated lottery person: {prize.associated_drawer}.")
        return " ".join(rules)

    def begin_round(self, prize: Prize) -> None:
        """Start a new round for the prize."""
        self._round_prize = prize
        self._round_winners = []

    def draw_next(self, prize: Prize) -> User | None:
        """Draw the next winner for the prize. Returns None if no candidate remains."""
        if self._round_prize is not prize:
            self.begin_round(prize)
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winner_keys.add(self._name_key(user))
        self._round_winners.append(user)
        return user

    def end_round(self, prize: Prize) -> list[User]:
        """Finish the round, update fallback history and return the round winners."""
        winners = list(self._round_winners)
        if self._drawer_key(prize) in _HISTORY_DRAWERS:
            contains_cheng_ru = any(self._is_cheng_ru(user) for user in winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        self._round_prize = None
        self._round_winners = []
        return winners
