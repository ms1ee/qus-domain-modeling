"""Lottery rule engine: eligibility pools, fallback protection and draws."""
from __future__ import annotations

import random

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _is_drawer(prize: Prize, drawer_name: str) -> bool:
    return prize.associated_drawer is not None and _norm(prize.associated_drawer) == _norm(drawer_name)


def _is_cheng_ru(user: User) -> bool:
    return _norm(user.department) == _norm(CHENG_RU_GROUP)


class LotteryManager:
    """Runs lottery draws for a participant list while enforcing all rules."""

    def __init__(self, users: list[User]) -> None:
        self._users: list[User] = list(users)
        self._winners: list[User] = []
        self._winner_names: set[str] = set()
        # Results of the most recent rounds drawn by Chen Qixian / Jin Duo:
        # True means the round produced at least one Cheng Ru Group winner.
        self.last_two_draw_results: list[bool] = []
        self._round_has_cheng_ru: bool = False

    @property
    def winners(self) -> list[User]:
        """Winners in the order they were drawn."""
        return list(self._winners)

    def is_fallback_active(self) -> bool:
        """Fallback (Cheng Ru protection) is active when the last two
        Chen Qixian / Jin Duo rounds both had no Cheng Ru Group winners."""
        return len(self.last_two_draw_results) == 2 and not any(self.last_two_draw_results)

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        """Compute the candidates eligible for the next draw of `prize`."""
        # Basic filtering: exclude all previous winners (anti-duplication).
        available = [u for u in self._users if u.name not in self._winner_names]

        # Fallback: Ma Jiaqi's prize is forced to Cheng Ru Group members,
        # even if that group is an avoidance group of the prize.
        if _is_drawer(prize, MA_JIAQI) and self.is_fallback_active():
            return [u for u in available if _is_cheng_ru(u)]

        # Special rule: Li Bin's prizes only filter previous winners.
        if _is_drawer(prize, LI_BIN):
            return available

        # Default: also apply avoidance groups.
        avoid = {_norm(g) for g in prize.avoid_groups if g and g.strip()}
        return [u for u in available if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        """Human-readable description of the rules applied to a prize round."""
        parts: list[str] = []
        if _is_drawer(prize, LI_BIN):
            parts.append("Previous winners are excluded; avoidance groups are NOT applied (special rule for Li Bin).")
        else:
            parts.append("Previous winners are excluded.")
            if prize.avoid_groups:
                parts.append(f"Avoidance groups: {', '.join(prize.avoid_groups)}.")
            else:
                parts.append("No avoidance groups.")
        if _is_drawer(prize, MA_JIAQI):
            if self.is_fallback_active():
                parts.append(
                    f"Fallback ACTIVE: candidates are limited to {CHENG_RU_GROUP} members."
                )
            else:
                parts.append(
                    f"Fallback ({CHENG_RU_GROUP} protection) is inactive; the last two "
                    f"Chen Qixian/Jin Duo rounds did not both lack {CHENG_RU_GROUP} winners."
                )
        return " ".join(parts)

    def draw_winner(self, prize: Prize) -> User | None:
        """Draw one winner for `prize`. Returns None if no eligible candidate remains."""
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = random.choice(pool)
        self._winners.append(winner)
        self._winner_names.add(winner.name)
        if (_is_drawer(prize, CHEN_QIXIAN) or _is_drawer(prize, JIN_DUO)) and _is_cheng_ru(winner):
            self._round_has_cheng_ru = True
        return winner

    def finish_round(self, prize: Prize) -> None:
        """Must be called when a round ends (completed, terminated or exhausted).
        Updates the fallback tracking state."""
        if _is_drawer(prize, CHEN_QIXIAN) or _is_drawer(prize, JIN_DUO):
            self.last_two_draw_results.append(self._round_has_cheng_ru)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif _is_drawer(prize, MA_JIAQI):
            # The fallback check has been consumed by this round; reset the window.
            self.last_two_draw_results = []
        self._round_has_cheng_ru = False
