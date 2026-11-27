"""Lottery rule engine: eligibility, avoidance, special rules and fallback."""

from __future__ import annotations

import random

from lottery_system.models import Prize, User, normalize_text

DRAWER_OPTIONS: tuple[str, ...] = ("Chen Qixian", "Jin Duo", "Ma Jiaqi", "Li Bin")

_SPECIAL_DRAWER = "li bin"
_FALLBACK_DRAWERS = ("chen qixian", "jin duo")
_PROTECTED_DRAWER = "ma jiaqi"
_PROTECTED_GROUP_KEYWORD = "cheng ru"


class LotteryManager:
    """Draws winners for prizes while enforcing the lottery rules."""

    def __init__(self, users: list[User], rng: random.Random | None = None) -> None:
        self.users: list[User] = list(users)
        # Results of the most recent rounds of Chen Qixian / Jin Duo:
        # True if that round produced at least one Cheng Ru group winner.
        self.last_two_draw_results: list[bool] = []
        self._drawn: set[str] = set()
        self._rng = rng if rng is not None else random.Random()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _name_key(name: str) -> str:
        return normalize_text(name)

    @staticmethod
    def is_cheng_ru_member(user: User) -> bool:
        """Return True if the user belongs to the Cheng Ru group."""
        return _PROTECTED_GROUP_KEYWORD in normalize_text(user.department)

    @staticmethod
    def _drawer_key(prize: Prize) -> str:
        return normalize_text(prize.associated_drawer or "")

    @staticmethod
    def _is_avoided(user: User, prize: Prize) -> bool:
        groups = {normalize_text(group) for group in prize.avoid_groups}
        return normalize_text(user.department) in groups

    def has_drawn(self, user: User) -> bool:
        """Return True if the user has already won a prize."""
        return self._name_key(user.name) in self._drawn

    def remaining_users(self) -> list[User]:
        """Return all users who have not won yet."""
        return [user for user in self.users if not self.has_drawn(user)]

    def is_protection_active(self) -> bool:
        """Return True if the Cheng Ru group protection must be applied."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    # ------------------------------------------------------------ rule engine
    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Return the primary pool of users eligible for the prize.

        - Previous winners are always excluded.
        - Li Bin: avoidance groups are not applied.
        - Ma Jiaqi with protection active: only Cheng Ru group members.
        - Otherwise members of the prize's avoidance groups are excluded from
          the primary pool; they are drawn only after the other members
          (see ``_get_deferred_pool``).
        """
        available = self.remaining_users()
        drawer = self._drawer_key(prize)

        if drawer == _SPECIAL_DRAWER:
            return available

        if drawer == _PROTECTED_DRAWER and self.is_protection_active():
            forced = [user for user in available if self.is_cheng_ru_member(user)]
            if forced:
                return forced

        return [user for user in available if not self._is_avoided(user, prize)]

    def _get_deferred_pool(self, prize: Prize) -> list[User]:
        """Return avoidance-group members who may be drawn after the primary pool."""
        if self._drawer_key(prize) == _SPECIAL_DRAWER:
            return []
        return [user for user in self.remaining_users() if self._is_avoided(user, prize)]

    def draw_one(self, prize: Prize) -> User | None:
        """Draw a single winner for the prize. Returns None if nobody is eligible."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_deferred_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        self._drawn.add(self._name_key(winner.name))
        return winner

    def finish_round(self, prize: Prize, winners: list[User]) -> None:
        """Update fallback state after a prize round has finished."""
        drawer = self._drawer_key(prize)
        if drawer in _FALLBACK_DRAWERS:
            has_protected = any(self.is_cheng_ru_member(user) for user in winners)
            self.last_two_draw_results.append(has_protected)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _PROTECTED_DRAWER:
            self.last_two_draw_results = []

    def rule_description(self, prize: Prize) -> str:
        """Return a human-readable description of the rules for the prize."""
        drawer = (prize.associated_drawer or "").strip()
        drawer_key = normalize_text(drawer)
        parts: list[str] = []

        if drawer_key == _SPECIAL_DRAWER:
            parts.append("Only previous winners are excluded; avoidance groups do not apply.")
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                groups = ", ".join(prize.avoid_groups)
                parts.append(
                    f"Members of avoidance groups ({groups}) are drawn only after other members."
                )
            if drawer_key == _PROTECTED_DRAWER:
                if self.is_protection_active():
                    parts.append(
                        "Cheng Ru Group protection is ACTIVE: only Cheng Ru Group members are eligible."
                    )
                else:
                    parts.append(
                        "Cheng Ru Group protection applies if the last two rounds of "
                        "Chen Qixian and Jin Duo had no Cheng Ru Group winners."
                    )

        if drawer:
            parts.insert(0, f"Lottery person: {drawer}.")
        else:
            parts.insert(0, "Lottery person: anyone.")
        return " ".join(parts)
