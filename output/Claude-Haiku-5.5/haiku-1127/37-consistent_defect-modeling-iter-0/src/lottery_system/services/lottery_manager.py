"""Lottery rule engine: filtering, avoidance tiers, special rules and fallback."""

import random

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")


def _norm(text) -> str:
    return " ".join(str(text).split()).casefold()


def _drawer_is(prize: Prize, drawer_name: str) -> bool:
    return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)


def describe_rule(prize: Prize) -> str:
    """Human readable rule description for a prize round."""
    parts: list[str] = []
    if _drawer_is(prize, LI_BIN):
        parts.append("Previous winners are excluded; avoidance groups are NOT applied.")
    else:
        parts.append("Previous winners are excluded.")
        if prize.avoid_groups:
            parts.append(
                f"Avoidance groups ({', '.join(prize.avoid_groups)}): members remain eligible "
                "but are drawn only after all other members."
            )
    if prize.associated_drawer:
        parts.append(f"Lottery person: {prize.associated_drawer}.")
    if _drawer_is(prize, MA_JIAQI):
        parts.append(
            "Fallback: if the last two draws of Chen Qixian and Jin Duo contained no "
            f"{CHENG_RU_GROUP} winners, the pool is limited to {CHENG_RU_GROUP} members."
        )
    return " ".join(parts)


class LotteryManager:
    """Draws winners while enforcing all lottery rules."""

    def __init__(self, users) -> None:
        self.users: list[User] = list(users)
        self.last_two_draw_results: list[bool] = []
        self._winner_keys: set[str] = set()
        self._current_round_winners: list[User] = []

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return _norm(user.department) == _norm(CHENG_RU_GROUP)

    def _is_winner(self, user: User) -> bool:
        return _norm(user.name) in self._winner_keys

    def _protected_candidates(self) -> list[User]:
        return [u for u in self.users if not self._is_winner(u) and self._is_cheng_ru(u)]

    def is_fallback_active(self, prize: Prize) -> bool:
        """True if the Cheng Ru group protection forces this prize's pool."""
        if not _drawer_is(prize, MA_JIAQI):
            return False
        if len(self.last_two_draw_results) < 2 or any(self.last_two_draw_results):
            return False
        return bool(self._protected_candidates())

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Eligible non-winners for the prize (fallback applied if active)."""
        if self.is_fallback_active(prize):
            return self._protected_candidates()
        return [u for u in self.users if not self._is_winner(u)]

    def _split_tiers(self, prize: Prize, pool: list[User]) -> tuple[list[User], list[User]]:
        """Split pool into (preferred, avoidance-group members drawn later)."""
        if _drawer_is(prize, LI_BIN):
            return list(pool), []
        avoid = {_norm(g) for g in prize.avoid_groups}
        primary = [u for u in pool if _norm(u.department) not in avoid]
        secondary = [u for u in pool if _norm(u.department) in avoid]
        return primary, secondary

    def draw_one(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        primary, secondary = self._split_tiers(prize, pool)
        tier = primary or secondary
        if not tier:
            return None
        winner = random.choice(tier)
        self._winner_keys.add(_norm(winner.name))
        self._current_round_winners.append(winner)
        return winner

    def end_round(self, prize: Prize) -> list[User]:
        """Finish the current round, updating fallback tracking. Returns round winners."""
        winners = self._current_round_winners
        self._current_round_winners = []
        if any(_drawer_is(prize, d) for d in FALLBACK_TRIGGER_DRAWERS):
            hit = any(self._is_cheng_ru(u) for u in winners)
            self.last_two_draw_results = (self.last_two_draw_results + [hit])[-2:]
        return winners
