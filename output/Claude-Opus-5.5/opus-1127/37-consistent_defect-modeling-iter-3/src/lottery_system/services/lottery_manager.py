"""Lottery rule engine and draw execution."""
import random
from typing import Dict, List, Optional

from lottery_system.models import Prize, User, normalize_group
from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
PROTECTED_GROUP = "Cheng Ru Group"
MONITORED_DRAWERS = ("Chen Qixian", "Jin Duo")
TRIGGERED_DRAWER = "Ma Jiaqi"

_PROTECTED_KEYS = {normalize_group("Cheng Ru Group"), normalize_group("Cheng Ru")}


def is_protected_group(department: str) -> bool:
    return normalize_group(department) in _PROTECTED_KEYS


def _same_person(a: Optional[str], b: str) -> bool:
    return a is not None and normalize_group(a) == normalize_group(b)


class LotteryManager:
    def __init__(self, users, result_manager: Optional[ResultManager] = None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = set(w.user.name for w in self.result_manager.winners)
        self.last_two_draw_results: List[bool] = []
        self.drawn_counts: Dict[str, int] = {}
        self.completed_prizes = set()

    # ---------- rule engine ----------
    def is_fallback_active(self, prize: Prize) -> bool:
        if not _same_person(prize.associated_drawer, TRIGGERED_DRAWER):
            return False
        r = self.last_two_draw_results
        return len(r) >= 2 and not r[-1] and not r[-2]

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            protected = [u for u in candidates if is_protected_group(u.department)]
            if protected:
                return protected
        if _same_person(prize.associated_drawer, SPECIAL_DRAWER):
            return candidates
        avoid = {normalize_group(g) for g in (prize.avoid_groups or [])}
        if not avoid:
            return candidates
        preferred = [u for u in candidates if normalize_group(u.department) not in avoid]
        if preferred:
            return preferred
        # Avoidance group members remain eligible but are drawn after others.
        return candidates

    # ---------- draw execution ----------
    def remaining(self, prize: Prize) -> int:
        return max(0, prize.quantity - self.drawn_counts.get(prize.name, 0))

    def draw_winner(self, prize: Prize) -> Optional[User]:
        if self.remaining(prize) <= 0:
            return None
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)
        self.drawn_counts[prize.name] = self.drawn_counts.get(prize.name, 0) + 1
        return user

    def finish_round(self, prize: Prize, round_winners: List[User]) -> None:
        self.completed_prizes.add(prize.name)
        drawer = prize.associated_drawer
        if any(_same_person(drawer, m) for m in MONITORED_DRAWERS):
            self.last_two_draw_results.append(
                any(is_protected_group(u.department) for u in round_winners)
            )
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif _same_person(drawer, TRIGGERED_DRAWER):
            self.last_two_draw_results = []

    def is_completed(self, prize: Prize) -> bool:
        return prize.name in self.completed_prizes
