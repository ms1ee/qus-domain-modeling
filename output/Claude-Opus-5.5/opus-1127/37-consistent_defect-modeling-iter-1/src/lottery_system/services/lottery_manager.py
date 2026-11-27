"""Lottery rule engine and round process control."""

from __future__ import annotations

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User, normalize_name
from lottery_system.services.result_manager import ResultManager, Winner


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    SPECIAL_DRAWER = "Li Bin"
    TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
    FALLBACK_DRAWER = "Ma Jiaqi"
    PROTECTED_GROUP = "Cheng Ru Group"

    def __init__(self, users, result_manager: Optional[ResultManager] = None) -> None:
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = {normalize_name(w.user.name) for w in self.result_manager.winners}
        self.last_two_draw_results: List[bool] = []
        self.fallback_applied = False
        self.rng = random.Random()

    # ----------------------------------------------------------------- helpers
    def _is_winner(self, user: User) -> bool:
        return normalize_name(user.name) in self.winner_names

    @classmethod
    def _is_protected(cls, user: User) -> bool:
        dept = normalize_name(user.department).replace(" ", "")
        return dept == "chengrugroup" or dept == "chengru" or dept.startswith("chengru")

    @staticmethod
    def _in_avoid(user: User, prize: Prize) -> bool:
        avoid = {normalize_name(g) for g in (prize.avoid_groups or [])}
        return normalize_name(user.department) in avoid

    def _is_special(self, prize: Prize) -> bool:
        return normalize_name(prize.associated_drawer) == normalize_name(self.SPECIAL_DRAWER)

    def _fallback_triggered(self, prize: Prize) -> bool:
        if normalize_name(prize.associated_drawer) != normalize_name(self.FALLBACK_DRAWER):
            return False
        hist = self.last_two_draw_results
        return len(hist) >= 2 and not any(hist[-2:])

    # ----------------------------------------------------------------- engine
    def _get_eligible_pool(self, prize) -> List[User]:
        available = [u for u in self.users if not self._is_winner(u)]
        if self._fallback_triggered(prize):
            protected = [u for u in available if self._is_protected(u)]
            if protected:
                return protected
        if self._is_special(prize):
            return available
        return [u for u in available if not self._in_avoid(u, prize)]

    def _get_secondary_pool(self, prize) -> List[User]:
        """Avoidance-group members: eligible only after all other members."""
        if self._is_special(prize):
            return []
        return [u for u in self.users if not self._is_winner(u) and self._in_avoid(u, prize)]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if self._is_special(prize):
            parts.append(f"Special lottery person '{drawer}': avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append(
                "Avoidance groups (drawn only after other members): "
                + ", ".join(prize.avoid_groups)
            )
        else:
            parts.append("No avoidance groups")
        if self._fallback_triggered(prize):
            parts.append(
                f"Fallback active: prize pool limited to '{self.PROTECTED_GROUP}' members"
            )
        if drawer:
            parts.insert(0, f"Lottery person: {drawer}")
        return "; ".join(parts)

    def draw_winner(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_secondary_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winner_names.add(normalize_name(user.name))
        self.result_manager.add_winner(user, prize)
        return user

    def _update_history(self, prize: Prize, round_users: List[User]) -> None:
        drawer = normalize_name(prize.associated_drawer)
        triggers = {normalize_name(t) for t in self.TRIGGER_DRAWERS}
        if drawer in triggers:
            self.last_two_draw_results.append(any(self._is_protected(u) for u in round_users))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == normalize_name(self.FALLBACK_DRAWER):
            self.last_two_draw_results = []
        elif drawer:
            self.last_two_draw_results = []

    # ----------------------------------------------------------------- rounds
    def run_round(
        self,
        prize: Prize,
        round_number: int = 1,
        input_func: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
        interactive: bool = True,
    ) -> List[Winner]:
        self.fallback_applied = self._fallback_triggered(prize)
        if self.fallback_applied:
            output(
                f"[Fallback] Neither {' nor '.join(self.TRIGGER_DRAWERS)} drew a "
                f"'{self.PROTECTED_GROUP}' member; this round is limited to that group."
            )
        round_users: List[User] = []
        start = len(self.result_manager.winners)
        terminated = False
        while len(round_users) < prize.quantity and not terminated:
            idx = len(round_users) + 1
            if interactive:
                try:
                    cmd = input_func(
                        f"[Round {round_number}] Press Enter to draw the {ordinal(idx)} winner "
                        "(commands: pause / continue / terminate): "
                    ).strip().lower()
                except EOFError:
                    cmd = ""
                if cmd == "pause":
                    output("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                    while True:
                        try:
                            c2 = input_func("(paused) > ").strip().lower()
                        except EOFError:
                            c2 = "terminate"
                        if c2 == "continue":
                            output("Lottery resumed.")
                            break
                        if c2 == "terminate":
                            terminated = True
                            break
                        output("Lottery is paused. Type 'continue' or 'terminate'.")
                elif cmd == "terminate":
                    terminated = True
                elif cmd == "continue":
                    output("Lottery is not paused, drawing continues.")
                elif cmd:
                    output(f"Unknown command '{cmd}', drawing continues.")
                if terminated:
                    output(f"Round {round_number} terminated; skipping remaining draws.")
                    break
            output(f"Currently drawing the {ordinal(idx)} winner...")
            user = self.draw_winner(prize)
            if user is None:
                output("No eligible participants remaining for this prize.")
                break
            round_users.append(user)
            output(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        self._update_history(prize, round_users)
        return self.result_manager.winners[start:]
