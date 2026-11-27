"""Lottery rule engine and round execution."""

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _is_protected(user: User) -> bool:
    return _norm(user.department) == _norm(PROTECTED_GROUP)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryManager:
    """Executes draws according to the rule engine."""

    def __init__(self, users, result_manager: Optional[ResultManager] = None) -> None:
        self.users: List[User] = list(users)
        self.result_manager = result_manager or ResultManager()
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []

    # ------------------------------------------------------------- rule engine
    def _fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize) -> List[User]:
        base = [u for u in self.users if u.name not in self.winner_names]
        if self._fallback_active(prize):
            protected = [u for u in base if _is_protected(u)]
            if protected:
                return protected
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return base
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in base if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        drawer = prize.associated_drawer or "N/A"
        if self._fallback_active(prize):
            return (f"Drawer: {drawer}. Fallback mechanism active: pool limited to "
                    f"'{PROTECTED_GROUP}' members (avoidance groups ignored).")
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return (f"Drawer: {drawer}. Special rule: only previous winners are "
                    f"excluded; avoidance groups are not applied.")
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        return f"Drawer: {drawer}. Excludes previous winners; avoidance groups: {groups}."

    def _record_drawer_result(self, prize: Prize, winners: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            self.last_two_draw_results.append(any(_is_protected(u) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_DRAWER):
            self.last_two_draw_results = []

    # --------------------------------------------------------------- execution
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = random.choice(pool)
        self.winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)
        return user

    def run_round(
        self,
        prize: Prize,
        command_reader: Optional[Callable[[str], str]] = None,
        printer: Callable[[str], None] = print,
    ) -> List[User]:
        """Run one prize round. command_reader=None draws automatically."""
        results: List[User] = []
        while len(results) < prize.quantity:
            n = len(results) + 1
            if command_reader is not None:
                cmd = command_reader(
                    f"[Enter] draw {ordinal(n)} winner / 'pause' / 'terminate': "
                ).strip().lower()
                if cmd == "pause":
                    printer("Lottery paused.")
                    terminated = False
                    while True:
                        c = command_reader("Paused. Type 'continue' or 'terminate': ").strip().lower()
                        if c == "continue":
                            printer("Lottery resumed.")
                            break
                        if c == "terminate":
                            terminated = True
                            break
                        printer("Invalid command while paused.")
                    if terminated:
                        printer(f"Round '{prize.name}' terminated.")
                        break
                    continue
                if cmd == "terminate":
                    printer(f"Round '{prize.name}' terminated.")
                    break
                if cmd not in ("", "continue", "draw"):
                    printer("Unknown command. Use Enter, 'pause', 'continue' or 'terminate'.")
                    continue
            printer(f"Currently drawing the {ordinal(n)} winner...")
            user = self.draw_one(prize)
            if user is None:
                printer("No eligible participants remain for this prize. Round ends.")
                break
            results.append(user)
            printer(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        self._record_drawer_result(prize, results)
        return results
