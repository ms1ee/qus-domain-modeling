"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

CHENG_RU_GROUP = "Cheng Ru Group"
RELAXED_RULE_DRAWER = "Li Bin"
FALLBACK_SOURCE_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
FALLBACK_HISTORY_SIZE = 2


def _key(text: str | None) -> str:
    return (text or "").strip().casefold()


def is_cheng_ru_member(user: User) -> bool:
    return _key(user.department) == _key(CHENG_RU_GROUP)


class LotteryManager:
    """Runs draws for a set of participants while enforcing lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Outcomes (True = winners contained Cheng Ru Group members) of the most
        # recent rounds drawn by the fallback source lottery persons.
        self.last_two_draw_results: list[bool] = []
        self._rng = rng if rng is not None else random.Random()
        self._winner_keys: set[str] = set()

    # ----- state helpers -------------------------------------------------
    def has_won(self, user: User) -> bool:
        return _key(user.name) in self._winner_keys

    def is_fallback_active(self) -> bool:
        """Fallback triggers when the last two source rounds had no Cheng Ru Group winner."""
        return (
            len(self.last_two_draw_results) == FALLBACK_HISTORY_SIZE
            and not any(self.last_two_draw_results)
        )

    def _is_relaxed(self, prize: Prize) -> bool:
        return _key(prize.associated_drawer) == _key(RELAXED_RULE_DRAWER)

    def _is_fallback_target(self, prize: Prize) -> bool:
        return _key(prize.associated_drawer) == _key(FALLBACK_TARGET_DRAWER)

    # ----- eligibility ---------------------------------------------------
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the users who may win this prize right now."""
        available = [user for user in self.users if not self.has_won(user)]

        # Fallback (Cheng Ru Group protection) overrides avoidance groups.
        if self._is_fallback_target(prize) and self.is_fallback_active():
            protected = [user for user in available if is_cheng_ru_member(user)]
            if protected:
                return protected

        # Special rule for Li Bin: avoidance groups are waived; previous winners are still excluded.
        if self._is_relaxed(prize):
            return available

        avoided = {_key(group) for group in prize.avoid_groups}
        return [user for user in available if _key(user.department) not in avoided]

    def count_eligible(self, prize: Prize) -> int:
        return len(self._get_eligible_pool(prize))

    def describe_rule(self, prize: Prize) -> str:
        """Human-readable description of the rules applying to a prize round."""
        rules: list[str] = []
        if prize.associated_drawer:
            rules.append(f"lottery person: {prize.associated_drawer}")
        rules.append("previous winners excluded")
        if self._is_relaxed(prize):
            rules.append("relaxed rules for Li Bin: avoidance groups waived")
        elif prize.avoid_groups:
            rules.append("avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("no avoidance groups")
        if self._is_fallback_target(prize) and self.is_fallback_active():
            rules.append(
                f"{CHENG_RU_GROUP} protection active: only {CHENG_RU_GROUP} members are eligible"
            )
        return "; ".join(rules)

    # ----- drawing -------------------------------------------------------
    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if no candidate is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._winner_keys.add(_key(winner.name))
        self.result_manager.add_winner(winner, prize)
        return winner

    def record_round_outcome(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback history after a round has finished."""
        drawer = _key(prize.associated_drawer)
        if drawer in {_key(name) for name in FALLBACK_SOURCE_DRAWERS}:
            hit = any(is_cheng_ru_member(winner) for winner in winners)
            self.last_two_draw_results.append(hit)
            del self.last_two_draw_results[:-FALLBACK_HISTORY_SIZE]
        elif drawer == _key(FALLBACK_TARGET_DRAWER):
            # The fallback cycle is consumed by the target lottery person's round.
            self.last_two_draw_results.clear()
