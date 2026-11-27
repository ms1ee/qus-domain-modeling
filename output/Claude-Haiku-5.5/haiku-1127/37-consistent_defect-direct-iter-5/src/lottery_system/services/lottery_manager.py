"""Lottery rule engine."""

from __future__ import annotations

import random

from ..constants import CHEN_QIXIAN, CHENG_RU_GROUP, JIN_DUO, LI_BIN, MA_JIAQI
from ..models import Prize, User, normalize_text


class LotteryManager:
    """Draws winners while applying the lottery rules.

    Rules:
    - Previous winners are always excluded (anti-duplication).
    - Special person "Li Bin": only previous winners are excluded; avoidance
      groups are not applied.
    - Other prizes: members of the prize's avoidance groups remain eligible but
      are drawn only after all other candidates.
    - Cheng Ru fallback: if neither of the last two draws by Chen Qixian / Jin Duo
      produced a Cheng Ru Group member, the next draw by Ma Jiaqi is limited to
      Cheng Ru Group members (overriding avoidance groups).
    """

    def __init__(self, users):
        self.users: list[User] = list(users)
        self._winner_keys: set[str] = set()
        self.winners: list[User] = []
        self.last_two_draw_results: list[bool] = []

    @staticmethod
    def _same_person(first, second) -> bool:
        return first is not None and normalize_text(first) == normalize_text(second)

    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)

    def _is_winner(self, user: User) -> bool:
        return normalize_text(user.name) in self._winner_keys

    def is_fallback_active(self, prize: Prize) -> bool:
        """True when the Cheng Ru protection fallback applies to this prize's draw."""
        if not self._same_person(prize.associated_drawer, MA_JIAQI):
            return False
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_tiers(self, prize: Prize) -> list[list[User]]:
        """Candidate tiers in draw priority order (earlier tiers drawn first)."""
        non_winners = [user for user in self.users if not self._is_winner(user)]
        drawer = prize.associated_drawer

        if self._same_person(drawer, LI_BIN):
            return [non_winners] if non_winners else []

        if self.is_fallback_active(prize):
            forced = [user for user in non_winners if self._is_cheng_ru(user)]
            if forced:
                return [forced]

        avoid = {normalize_text(group) for group in prize.avoid_groups}
        primary = [u for u in non_winners if normalize_text(u.department) not in avoid]
        deferred = [u for u in non_winners if normalize_text(u.department) in avoid]
        return [tier for tier in (primary, deferred) if tier]

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """All currently eligible users for the prize, in draw priority order."""
        pool: list[User] = []
        for tier in self._get_tiers(prize):
            pool.extend(tier)
        return pool

    def draw_winner(self, prize: Prize):
        """Draw one winner for the prize. Returns User, or None if nobody is eligible."""
        winner = None
        for tier in self._get_tiers(prize):
            if tier:
                winner = random.choice(tier)
                break
        if winner is None:
            return None

        self._winner_keys.add(normalize_text(winner.name))
        self.winners.append(winner)

        if any(self._same_person(prize.associated_drawer, person)
               for person in (CHEN_QIXIAN, JIN_DUO)):
            self.last_two_draw_results.append(self._is_cheng_ru(winner))
            del self.last_two_draw_results[:-2]
        return winner

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize."""
        rules = ["previous winners are excluded"]
        drawer = prize.associated_drawer
        if drawer:
            rules.append(f"lottery person: {drawer}")

        if self._same_person(drawer, LI_BIN):
            rules.append("special rule for Li Bin: avoidance groups are NOT applied")
        elif self.is_fallback_active(prize):
            rules.append(
                f"Cheng Ru protection active: only {CHENG_RU_GROUP} members are eligible"
            )
        elif prize.avoid_groups:
            rules.append(
                "avoidance groups " + ", ".join(prize.avoid_groups)
                + ": members are drawn after other candidates"
            )
        return "; ".join(rules)
