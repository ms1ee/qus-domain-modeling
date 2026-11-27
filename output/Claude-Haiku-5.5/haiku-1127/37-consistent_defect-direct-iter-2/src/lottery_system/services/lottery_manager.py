"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User


LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
CHENG_RU_GROUP = "Cheng Ru Group"


def _norm(text: str | None) -> str:
    """Normalize text for case- and whitespace-insensitive comparison."""
    return " ".join((text or "").split()).casefold()


def is_cheng_ru_member(user: User) -> bool:
    """Return True if the user belongs to the Cheng Ru group."""
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


def describe_rules(prize: Prize) -> str:
    """Build a human-readable description of the rules of a prize round."""
    parts = ["Previous winners are excluded."]
    drawer = _norm(prize.associated_drawer)
    if prize.avoid_groups:
        parts.append(
            "Avoidance groups (drawn after other members): "
            + ", ".join(prize.avoid_groups)
            + "."
        )
    else:
        parts.append("No avoidance groups.")
    if prize.associated_drawer:
        parts.append(f"Lottery person: {prize.associated_drawer}.")
    if drawer == _norm(LI_BIN):
        parts.append("Special rule: avoidance groups are NOT applied for this lottery person.")
    if drawer == _norm(MA_JIAQI):
        parts.append(
            "Cheng Ru Group protection: if the last two lottery persons "
            "had no Cheng Ru Group winner, only Cheng Ru Group members are eligible."
        )
    return " ".join(parts)


class LotteryManager:
    """Performs draws while enforcing all lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winners: list[User] = []
        self._winner_names: set[str] = set()
        self._rng = rng or random.Random()
        # Results of the most recent lottery persons' rounds:
        # True means the round contained a Cheng Ru Group winner.
        self.last_two_draw_results: list[bool] = []

    @property
    def winners(self) -> list[User]:
        """All winners drawn so far, in winning order."""
        return list(self._winners)

    def is_winner(self, user: User) -> bool:
        """Return True if the user has already won any prize."""
        return user.name.strip() in self._winner_names

    def is_cheng_ru_protection_active(self, prize: Prize) -> bool:
        """Return True if the Cheng Ru group fallback restricts this prize's pool."""
        return (
            _norm(prize.associated_drawer) == _norm(MA_JIAQI)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users that may be drawn for the given prize right now."""
        available = [user for user in self._users if not self.is_winner(user)]
        drawer = _norm(prize.associated_drawer)

        # Special rule: Li Bin only filters previous winners.
        if drawer == _norm(LI_BIN):
            return available

        # Fallback: force the pool to Cheng Ru Group members, ignoring avoidance groups.
        if self.is_cheng_ru_protection_active(prize):
            cheng_ru_pool = [user for user in available if is_cheng_ru_member(user)]
            if cheng_ru_pool:
                return cheng_ru_pool

        avoid = {_norm(group) for group in prize.avoid_groups}
        primary = [user for user in available if _norm(user.department) not in avoid]
        if primary:
            return primary

        # Avoidance-group members remain eligible but are drawn only after everyone else.
        return [user for user in available if _norm(user.department) in avoid]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winners.append(winner)
        self._winner_names.add(winner.name.strip())
        return winner

    def finish_round(self, prize: Prize, round_winners: list[User]) -> None:
        """Record the outcome of a completed round for the fallback mechanism."""
        if not prize.associated_drawer:
            return
        had_cheng_ru = any(is_cheng_ru_member(user) for user in round_winners)
        self.last_two_draw_results.append(had_cheng_ru)
        self.last_two_draw_results = self.last_two_draw_results[-2:]
