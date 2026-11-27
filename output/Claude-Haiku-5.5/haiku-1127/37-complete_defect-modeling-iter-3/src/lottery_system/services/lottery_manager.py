"""Lottery rule engine: eligibility filtering, drawing and fallback protection."""

import random
from typing import List, Optional

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    is_cheng_ru_group,
    is_same_text,
    normalize_text,
)
from lottery_system.models import Prize, User


class LotteryManager:
    """Runs lottery draws for a set of participants while enforcing rules."""

    TRACKED_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
    PROTECTED_DRAWER = MA_JIAQI

    def __init__(self, users):
        self._users: List[User] = list(users)
        self._winner_keys = set()
        self._winners: List[User] = []
        self._random = random.Random()
        # Results (True = contained Cheng Ru group members) of the last two
        # rounds drawn by Chen Qixian / Jin Duo.
        self.last_two_draw_results: List[bool] = []

    @property
    def winners(self) -> List[User]:
        """Winners in the order they were drawn."""
        return list(self._winners)

    def has_won(self, user: User) -> bool:
        """Return True if the person has already won any prize."""
        return normalize_text(user.name) in self._winner_keys

    def _is_cheng_ru_protection_active(self) -> bool:
        """Protection triggers when the last two tracked results both lack Cheng Ru members."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        """Compute the set of participants that may win the given prize."""
        available = [user for user in self._users if not self.has_won(user)]
        drawer = prize.associated_drawer

        # Special rule: Li Bin only triggers the previous-winner filter.
        if drawer and is_same_text(drawer, LI_BIN):
            return available

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members,
        # even if that group is an avoidance group of this prize.
        if drawer and is_same_text(drawer, self.PROTECTED_DRAWER) and self._is_cheng_ru_protection_active():
            protected = [user for user in available if is_cheng_ru_group(user.department)]
            if protected:
                return protected

        avoided = {normalize_text(group) for group in prize.avoid_groups}
        return [user for user in available if normalize_text(user.department) not in avoided]

    def eligible_pool(self, prize: Prize) -> List[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> Optional[User]:
        """Draw one winner for the prize. Returns None if no eligible participant remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._random.choice(pool)
        self._winners.append(winner)
        self._winner_keys.add(normalize_text(winner.name))
        return winner

    def end_round(self, prize: Prize, round_winners) -> None:
        """Record the outcome of a finished round for the fallback mechanism."""
        drawer = prize.associated_drawer
        if drawer and any(is_same_text(drawer, name) for name in self.TRACKED_DRAWERS):
            hit = any(is_cheng_ru_group(user.department) for user in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def describe_rules(self, prize: Prize) -> str:
        """Return a human-readable description of the rules applied to a prize round."""
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer

        if drawer:
            parts.append(f"Lottery person: {drawer}")
        else:
            parts.append("No lottery person specified")

        if drawer and is_same_text(drawer, LI_BIN):
            parts.append("Special rule: avoidance groups are not applied")
        elif prize.avoid_groups:
            parts.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")

        if drawer and is_same_text(drawer, self.PROTECTED_DRAWER):
            if self._is_cheng_ru_protection_active():
                parts.append(f"Cheng Ru group protection active: pool limited to {CHENG_RU_GROUP} members")
            else:
                parts.append("Cheng Ru group protection not triggered")

        return "; ".join(parts)
