"""Lottery rule engine: eligibility filtering, special rules and draws."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


def _is_drawer(prize: Prize, drawer_name: str) -> bool:
    return _norm(prize.associated_drawer) == _norm(drawer_name) and bool(
        _norm(prize.associated_drawer)
    )


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Draws winners while enforcing the lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # Results (True = contained Cheng Ru Group member) of the two most recent
        # draws by lottery persons Chen Qixian / Jin Duo.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()

    @property
    def winner_names(self) -> set[str]:
        return set(self._winner_names)

    def is_relaxed(self, prize: Prize) -> bool:
        """Li Bin as lottery person: relaxed filtering (avoidance groups ignored)."""
        return _is_drawer(prize, LI_BIN)

    def is_cheng_ru_protected(self, prize: Prize) -> bool:
        """Ma Jiaqi's prize is limited to Cheng Ru Group when the two previous
        Chen Qixian / Jin Duo draws both contained no Cheng Ru Group member."""
        return (
            _is_drawer(prize, MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = [u for u in self._users if u.name not in self._winner_names]

        if self.is_cheng_ru_protected(prize):
            protected = [u for u in available if _is_cheng_ru(u)]
            if protected:
                return protected  # overrides avoidance groups

        if self.is_relaxed(prize):
            return available

        avoided = {_norm(group) for group in prize.avoid_groups}
        return [u for u in available if _norm(u.department) not in avoided]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single eligible winner, or None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_names.add(winner.name)
        return winner

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applying to a prize round."""
        rules = ["previous winners are excluded"]
        if self.is_relaxed(prize):
            rules.append("lottery person Li Bin: relaxed rules, avoidance groups not applied")
        elif prize.avoid_groups:
            rules.append("avoidance groups excluded: " + ", ".join(prize.avoid_groups))
        if self.is_cheng_ru_protected(prize):
            rules.append(
                "Cheng Ru Group protection active: only Cheng Ru Group members are eligible"
            )
        if prize.associated_drawer:
            rules.append(f"lottery person: {prize.associated_drawer}")
        return "; ".join(rules)

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback-mechanism state after a round has ended."""
        if _is_drawer(prize, CHEN_QIXIAN) or _is_drawer(prize, JIN_DUO):
            has_cheng_ru = any(_is_cheng_ru(u) for u in winners)
            self.last_two_draw_results.append(has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self.is_cheng_ru_protected(prize):
            # The protection window has been consumed by this Ma Jiaqi round.
            self.last_two_draw_results = []
