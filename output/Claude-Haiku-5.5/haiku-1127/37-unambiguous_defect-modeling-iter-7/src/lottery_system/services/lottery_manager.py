"""Lottery rule engine: eligibility filtering and winner drawing."""

import random

from lottery_system.constants import (
    CHENG_RU_GROUP,
    DRAWER_CHEN_QIXIAN,
    DRAWER_JIN_DUO,
    DRAWER_LI_BIN,
    DRAWER_MA_JIAQI,
)


def is_cheng_ru_member(user):
    """Return True if the user belongs to the Cheng Ru group."""
    return user.department.strip().lower() == CHENG_RU_GROUP.lower()


def _is_drawer(prize, drawer_name):
    drawer = (prize.associated_drawer or "").strip().lower()
    return drawer == drawer_name.lower()


class LotteryManager:
    """Runs lottery rounds over a fixed list of users."""

    def __init__(self, users):
        self.users = list(users)
        self.winner_names = set()
        # Results (True = contained a Cheng Ru member) of the most recent two
        # rounds drawn by Chen Qixian or Jin Duo.
        self.last_two_draw_results = []
        self._rng = random.Random()

    def is_fallback_active(self):
        """True when the Cheng Ru fallback protection is triggered."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize):
        """Return users eligible to win the given prize in the current state."""
        available = [user for user in self.users if user.name not in self.winner_names]

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru members, overriding
        # avoidance groups.
        if _is_drawer(prize, DRAWER_MA_JIAQI) and self.is_fallback_active():
            return [user for user in available if is_cheng_ru_member(user)]

        # Special rule: Li Bin relaxes filtering (only anti-duplication applies).
        if _is_drawer(prize, DRAWER_LI_BIN):
            return available

        avoid = {group.strip().lower() for group in prize.avoid_groups}
        return [user for user in available if user.department.strip().lower() not in avoid]

    def get_eligible_pool(self, prize):
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize):
        """Draw a single winner for the prize. Returns the User or None."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self.winner_names.add(winner.name)
        return winner

    def finish_round(self, prize, round_winners):
        """Record the outcome of a finished round for the fallback rule."""
        if _is_drawer(prize, DRAWER_CHEN_QIXIAN) or _is_drawer(prize, DRAWER_JIN_DUO):
            contains_cheng_ru = any(is_cheng_ru_member(user) for user in round_winners)
            self.last_two_draw_results.append(contains_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def describe_rules(self, prize):
        """Return human-readable rule descriptions for the prize's round."""
        rules = [
            "Previous winners are excluded (anti-duplication).",
            f"Lottery person: {prize.associated_drawer or 'None'}.",
        ]
        if _is_drawer(prize, DRAWER_LI_BIN):
            rules.append("Relaxed rule (Li Bin): avoidance groups are not applied.")
        elif prize.avoid_groups:
            rules.append(f"Avoidance groups excluded: {', '.join(prize.avoid_groups)}.")
        else:
            rules.append("No avoidance groups.")

        if _is_drawer(prize, DRAWER_MA_JIAQI):
            if self.is_fallback_active():
                rules.append(
                    "Cheng Ru fallback ACTIVE: only Cheng Ru Group members are eligible "
                    "(avoidance groups overridden)."
                )
            else:
                rules.append(
                    "Cheng Ru fallback: if neither of the last two Chen Qixian/Jin Duo "
                    "rounds had a Cheng Ru Group winner, only Cheng Ru Group members "
                    "can win."
                )
        return rules
