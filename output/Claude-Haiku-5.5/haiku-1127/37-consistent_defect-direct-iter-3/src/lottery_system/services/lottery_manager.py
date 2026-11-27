"""Lottery rule engine: eligibility filtering, special rules and fallback protection."""

from __future__ import annotations

import random

from lottery_system.models import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
    normalize_text,
)


def is_cheng_ru_member(user: User) -> bool:
    """True if the user belongs to the Cheng Ru group."""
    return normalize_text(user.department) == normalize_text(CHENG_RU_GROUP)


class LotteryManager:
    """Runs draws while enforcing the lottery rules.

    Rules:
    - Previous winners are always excluded (anti-duplication, any prize type).
    - Members of a prize's avoidance groups are drawn only after other members.
    - Lottery person Li Bin: only previous winners are excluded; avoidance groups are ignored.
    - Cheng Ru protection: if the last two draws by Chen Qixian / Jin Duo contained no
      Cheng Ru group member, Ma Jiaqi's prize pool is limited to Cheng Ru group members.
    """

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winner_names: set[str] = set()
        # True means the draw winner belonged to the Cheng Ru group.
        self.last_two_draw_results: list[bool] = []

    def has_won(self, user: User) -> bool:
        return user.name in self._winner_names

    def mark_winner(self, user: User) -> None:
        self._winner_names.add(user.name)

    def get_available_users(self) -> list[User]:
        """Users who have not won yet."""
        return [user for user in self._users if user.name not in self._winner_names]

    def _cheng_ru_protection_active(self, prize: Prize) -> bool:
        return (
            normalize_text(prize.associated_drawer) == normalize_text(MA_JIAQI)
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        available = self.get_available_users()
        drawer = normalize_text(prize.associated_drawer)

        # Special rule: Li Bin only filters previous winners.
        if drawer == normalize_text(LI_BIN):
            return available

        # Fallback protection: force Cheng Ru group members when protection is active.
        if self._cheng_ru_protection_active(prize):
            protected = [user for user in available if is_cheng_ru_member(user)]
            if protected:
                return protected

        # Avoidance groups: non-avoided members first; avoided members only afterwards.
        avoid = {normalize_text(group) for group in prize.avoid_groups}
        preferred = [user for user in available if normalize_text(user.department) not in avoid]
        return preferred if preferred else available

    def draw(self, prize: Prize) -> User | None:
        """Draw one winner for the prize. Returns None if no eligible user remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self.mark_winner(winner)
        self._record_draw(prize, winner)
        return winner

    def _record_draw(self, prize: Prize, winner: User) -> None:
        drawer = normalize_text(prize.associated_drawer)
        if drawer in (normalize_text(CHEN_QIXIAN), normalize_text(JIN_DUO)):
            self.last_two_draw_results.append(is_cheng_ru_member(winner))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == normalize_text(MA_JIAQI):
            # The protection window is consumed by Ma Jiaqi's draw.
            self.last_two_draw_results = []

    @staticmethod
    def describe_rule(prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        drawer = normalize_text(prize.associated_drawer)
        parts: list[str] = []
        if drawer == normalize_text(LI_BIN):
            parts.append(
                "Previous winners are excluded; avoidance groups are NOT applied "
                "for this lottery person"
            )
        else:
            parts.append("Previous winners are excluded")
            if prize.avoid_groups:
                groups = ", ".join(prize.avoid_groups)
                parts.append(
                    f"members of avoidance group(s) [{groups}] are drawn only after other members"
                )
            if drawer == normalize_text(MA_JIAQI):
                parts.append(
                    "Cheng Ru Group protection: if the last two draws by Chen Qixian and "
                    "Jin Duo had no Cheng Ru Group winner, only Cheng Ru Group members are eligible"
                )
        return "; ".join(parts) + "."
