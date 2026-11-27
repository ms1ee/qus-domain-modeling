"""Lottery rule engine: eligibility pools, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User, normalize_text


LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru Group"


class LotteryManager:
    """Runs draws while enforcing all lottery rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.drawn_winners: list[User] = []
        # Per-round flags for draws by Chen Qixian / Jin Duo:
        # True if the round produced at least one Cheng Ru group member.
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _name_key(user: User) -> str:
        return normalize_text(user.name)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)

    @staticmethod
    def _drawer_key(prize: Prize) -> str:
        return normalize_text(prize.associated_drawer or "")

    def is_winner(self, user: User) -> bool:
        """Return True if the user has already won in any round."""
        return self._name_key(user) in self._winner_keys

    def fallback_active(self) -> bool:
        """Cheng Ru protection triggers when the last two Chen/Jin draws had no Cheng Ru member."""
        return len(self.last_two_draw_results) >= 2 and not any(self.last_two_draw_results[-2:])

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the list of users eligible for the given prize at this moment."""
        available = [u for u in self._users if not self.is_winner(u)]
        drawer = self._drawer_key(prize)

        # Special rule: Li Bin draws only filter previous winners.
        if drawer == normalize_text(LI_BIN):
            return available

        # Fallback: Ma Jiaqi's pool is forced to Cheng Ru group members,
        # overriding avoidance groups.
        if drawer == normalize_text(MA_JIAQI) and self.fallback_active():
            return [u for u in available if self._is_cheng_ru(u)]

        avoid = {normalize_text(g) for g in prize.avoid_groups}
        return [u for u in available if normalize_text(u.department) not in avoid]

    def get_eligible_pool(self, prize: Prize) -> list[User]:
        """Public accessor for the eligible pool of a prize."""
        return self._get_eligible_pool(prize)

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible participant remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winner_keys.add(self._name_key(winner))
        self.drawn_winners.append(winner)
        return winner

    def complete_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Record the outcome of a finished round for fallback tracking."""
        drawer = self._drawer_key(prize)
        if drawer in (normalize_text(CHEN_QIXIAN), normalize_text(JIN_DUO)):
            hit = any(self._is_cheng_ru(u) for u in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to this prize."""
        rules: list[str] = []
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        rules.append("previous winners are excluded")
        drawer = self._drawer_key(prize)
        if drawer == normalize_text(LI_BIN):
            rules.append("special rule for Li Bin: avoidance groups are not applied")
        else:
            if prize.avoid_groups:
                rules.append("avoided groups: " + ", ".join(prize.avoid_groups))
            if drawer == normalize_text(MA_JIAQI) and self.fallback_active():
                rules.append(f"fallback active: only {CHENG_RU_GROUP} members are eligible")
        return "; ".join(rules)
