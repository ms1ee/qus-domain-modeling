"""Lottery rule engine: eligible pool calculation and winner drawing."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User, normalize


CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


class LotteryManager:
    """Applies lottery rules and tracks winners across all rounds."""

    def __init__(self, users):
        self.users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.winners: list[User] = []
        # Results of the most recent draws made by Chen Qixian / Jin Duo.
        # True means the drawn winner belonged to the Cheng Ru Group.
        self.last_two_draw_results: list[bool] = []
        self._rng = random.Random()

    def is_winner(self, user: User) -> bool:
        return normalize(user.name) in self._winner_keys

    def _is_cheng_ru(self, user: User) -> bool:
        return normalize(user.department) == normalize(CHENG_RU_GROUP)

    def _available_users(self) -> list[User]:
        return [user for user in self.users if not self.is_winner(user)]

    def _fallback_active(self) -> bool:
        """True when the last two draws by Chen Qixian / Jin Duo both had no Cheng Ru Group member."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the pool that the next winner of this prize is drawn from.

        - Previous winners are always excluded.
        - Special rule (Li Bin): avoidance groups are not applied.
        - Fallback (Ma Jiaqi): when the last two draws by Chen Qixian and Jin Duo
          had no Cheng Ru Group member, the pool is limited to Cheng Ru Group
          members (even if that group is an avoidance group). If no such member
          is available, the normal rules apply.
        - Avoidance groups: members of avoidance groups are drawn only after all
          other eligible members have been drawn.
        """
        available = self._available_users()
        drawer = normalize(prize.associated_drawer) if prize.associated_drawer else ""

        if drawer == normalize(LI_BIN):
            return available

        if drawer == normalize(MA_JIAQI) and self._fallback_active():
            protected = [user for user in available if self._is_cheng_ru(user)]
            if protected:
                return protected

        avoid = {normalize(group) for group in prize.avoid_groups}
        primary = [user for user in available if normalize(user.department) not in avoid]
        if primary:
            return primary
        return [user for user in available if normalize(user.department) in avoid]

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible participant remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(normalize(winner.name))
        self.winners.append(winner)

        drawer = normalize(prize.associated_drawer) if prize.associated_drawer else ""
        if drawer in (normalize(CHEN_QIXIAN), normalize(JIN_DUO)):
            self.last_two_draw_results.append(self._is_cheng_ru(winner))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        return winner

    def describe_rules(self, prize: Prize) -> list[str]:
        """Return human-readable descriptions of the rules applied to a prize round."""
        rules = ["Previous winners are excluded (no one can win twice)."]
        drawer = normalize(prize.associated_drawer) if prize.associated_drawer else ""
        if drawer == normalize(LI_BIN):
            rules.append("Special rule (Li Bin): avoidance groups do not apply.")
        else:
            if prize.avoid_groups:
                rules.append(
                    "Avoidance groups (members drawn only after other members): "
                    + ", ".join(prize.avoid_groups)
                    + "."
                )
            if drawer == normalize(MA_JIAQI):
                rules.append(
                    "Cheng Ru Group protection: if the last two draws by Chen Qixian and Jin Duo "
                    "contained no Cheng Ru Group member, this draw is limited to Cheng Ru Group members."
                )
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}.")
        return rules
