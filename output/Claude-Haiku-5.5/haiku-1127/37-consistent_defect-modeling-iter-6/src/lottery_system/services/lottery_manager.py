"""Lottery rule engine."""

import random

from lottery_system import config
from lottery_system.models import FallbackRule


def _norm(text):
    return (text or "").strip().lower()


class LotteryManager:
    """Applies lottery rules and performs draws.

    Rules:
    - Previous winners are always excluded (anti-duplication).
    - Lottery person 'Li Bin' only excludes previous winners.
    - Members of a prize's avoidance groups remain eligible, but are only drawn
      after all other eligible members have been drawn.
    - Cheng Ru group protection: if the last two draws made by Chen Qixian / Jin Duo
      contained no Cheng Ru group member, the next draw by Ma Jiaqi is limited to
      Cheng Ru group members (overriding avoidance groups). The history is reset
      once Ma Jiaqi's round ends.
    """

    def __init__(self, users):
        self._users = list(users)
        self._winner_names = set()
        self.last_two_draw_results = []
        self.fallback_rule = FallbackRule()
        self._rng = random.Random()

    def get_remaining_users(self):
        return [user for user in self._users if user.name not in self._winner_names]

    def _fallback_active(self, drawer_norm):
        rule = self.fallback_rule
        if not rule.active or drawer_norm != _norm(config.FALLBACK_TARGET_DRAWER):
            return False
        limit = rule.consecutive_miss_limit
        history = self.last_two_draw_results
        if len(history) < limit:
            return False
        return not any(history[-limit:])

    def _get_eligible_pool(self, prize):
        """Return the users from which the next winner of this prize is drawn."""
        available = self.get_remaining_users()
        drawer = _norm(prize.associated_drawer)

        if drawer == _norm(config.SPECIAL_DRAWER_LI_BIN):
            return available

        if self._fallback_active(drawer):
            protected = _norm(self.fallback_rule.protected_group)
            protected_members = [
                user for user in available if _norm(user.department) == protected
            ]
            if protected_members:
                return protected_members

        avoid = {_norm(group) for group in prize.avoid_groups if _norm(group)}
        primary = [user for user in available if _norm(user.department) not in avoid]
        if primary:
            return primary
        return [user for user in available if _norm(user.department) in avoid]

    def has_eligible(self, prize):
        return bool(self._get_eligible_pool(prize))

    def _record_draw_result(self, hit_protected_group):
        limit = self.fallback_rule.consecutive_miss_limit
        self.last_two_draw_results.append(bool(hit_protected_group))
        self.last_two_draw_results = self.last_two_draw_results[-limit:]

    def draw_one(self, prize):
        """Draw one winner for the prize. Returns User or None if no one is eligible."""
        pool = self._get_eligible_pool(prize)
        winner = self._rng.choice(pool) if pool else None

        drawer = _norm(prize.associated_drawer)
        trigger_drawers = {_norm(name) for name in config.FALLBACK_TRIGGER_DRAWERS}
        if drawer in trigger_drawers:
            hit = winner is not None and _norm(winner.department) == _norm(
                self.fallback_rule.protected_group
            )
            self._record_draw_result(hit)

        if winner is not None:
            self._winner_names.add(winner.name)
        return winner

    def end_round(self, prize):
        """Called when a round finishes. Resets the fallback history after Ma Jiaqi's round."""
        if _norm(prize.associated_drawer) == _norm(config.FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []

    def describe_rule(self, prize):
        """Human readable rule description for a round."""
        parts = []
        drawer = _norm(prize.associated_drawer)
        if not drawer:
            parts.append("No associated lottery person.")
        if drawer == _norm(config.SPECIAL_DRAWER_LI_BIN):
            parts.append(
                "Lottery person Li Bin: only previous winners are excluded; "
                "avoidance groups do not apply."
            )
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                parts.append(
                    "Avoidance group(s) "
                    + ", ".join(prize.avoid_groups)
                    + " remain eligible but are drawn after other members."
                )
            if self._fallback_active(drawer):
                parts.append(
                    f"Cheng Ru group protection active: pool limited to {config.CHENG_RU_GROUP} members."
                )
        if drawer in {_norm(name) for name in config.FALLBACK_TRIGGER_DRAWERS}:
            parts.append("Results feed the Cheng Ru group protection check.")
        return " ".join(parts)
