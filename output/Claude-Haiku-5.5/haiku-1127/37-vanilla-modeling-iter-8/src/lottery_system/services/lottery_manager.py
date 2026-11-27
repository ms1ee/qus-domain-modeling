"""Lottery rule engine: eligibility filtering, fallback protection and drawing."""

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
    describe_prize_rules,
    normalize,
    same_name,
)


def is_cheng_ru(user: User) -> bool:
    """Return True if the user belongs to the Cheng Ru group."""
    return normalize(user.department) == normalize(CHENG_RU_GROUP)


class LotteryManager:
    """Applies lottery rules and draws winners one at a time.

    Usage per round: begin_round(prize), draw_next(prize) repeatedly,
    then end_round(prize).
    """

    def __init__(self, users: list[User]) -> None:
        self.users: list[User] = list(users)
        # Results of the last two Chen Qixian / Jin Duo rounds:
        # True if the round produced at least one Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()
        self._winners: list[User] = []
        self._round_has_cheng_ru: bool = False
        self._fallback_active: bool = False

    @property
    def winners(self) -> list[User]:
        """All winners drawn so far, in winning order."""
        return list(self._winners)

    def is_fallback_triggered(self, prize: Prize) -> bool:
        """Return True if the prize is drawn by Ma Jiaqi and the Cheng Ru
        protection fallback is in effect (last two results both without
        Cheng Ru group members)."""
        if not prize.associated_drawer or not same_name(prize.associated_drawer, MA_JIAQI):
            return False
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the users who may be drawn for the given prize."""
        available = [
            user for user in self.users if normalize(user.name) not in self._winner_names
        ]

        if self.is_fallback_triggered(prize):
            forced = [user for user in available if is_cheng_ru(user)]
            if forced:
                return forced

        drawer = prize.associated_drawer
        if drawer and same_name(drawer, LI_BIN):
            return available

        avoided = {normalize(group) for group in prize.avoid_groups}
        return [user for user in available if normalize(user.department) not in avoided]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the current eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def describe_rule(self, prize: Prize) -> str:
        """Return the rule description shown to the operator for a prize."""
        text = describe_prize_rules(prize)
        if self.is_fallback_triggered(prize):
            text += " [Fallback ACTIVE for this round]"
        return text

    def begin_round(self, prize: Prize) -> None:
        """Prepare internal state before drawing for a prize."""
        self._round_has_cheng_ru = False
        self._fallback_active = self.is_fallback_triggered(prize)

    def draw_next(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self._winners.append(user)
        self._winner_names.add(normalize(user.name))
        if is_cheng_ru(user):
            self._round_has_cheng_ru = True
        return user

    def end_round(self, prize: Prize) -> None:
        """Update fallback tracking after a round finishes or is terminated."""
        drawer = prize.associated_drawer
        if drawer and (same_name(drawer, CHEN_QIXIAN) or same_name(drawer, JIN_DUO)):
            self.last_two_draw_results.append(self._round_has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer and same_name(drawer, MA_JIAQI) and self._fallback_active:
            # The protection has been applied; start counting afresh.
            self.last_two_draw_results = []
        self._round_has_cheng_ru = False
        self._fallback_active = False
