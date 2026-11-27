"""Lottery process control and rule engine."""

from __future__ import annotations

import random
from typing import Callable, List, Optional

from lottery_system.models import (
    FALLBACK_TARGET_DRAWER,
    FALLBACK_TRIGGER_DRAWERS,
    PROTECTED_GROUP,
    SPECIAL_DRAWER,
    User,
    is_protected_group,
    normalize_name,
)
from lottery_system.services.result_manager import ResultManager


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    """Executes lottery rounds applying all rules."""

    def __init__(self, users, result_manager: Optional[ResultManager] = None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = set(w.user.name for w in self.result_manager.winners)
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ------------------------------------------------------------ rule engine
    @staticmethod
    def _is_drawer(prize, name: str) -> bool:
        return normalize_name(getattr(prize, "associated_drawer", None)) == normalize_name(name)

    def _fallback_triggered(self, prize) -> bool:
        if not self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results[-2:])

    def _available_users(self) -> List[User]:
        return [u for u in self.users if u.name not in self.winner_names]

    def _get_eligible_pool(self, prize) -> List[User]:
        base = self._available_users()
        if self._is_drawer(prize, SPECIAL_DRAWER):
            return base
        if self._fallback_triggered(prize):
            protected = [u for u in base if is_protected_group(u.department)]
            if protected:
                return protected
        avoid = set(g.strip() for g in (prize.avoid_groups or []))
        return [u for u in base if u.department not in avoid]

    def describe_pool_rule(self, prize) -> str:
        if self._is_drawer(prize, SPECIAL_DRAWER):
            return f"Special drawer {SPECIAL_DRAWER}: only previous winners are excluded."
        if self._fallback_triggered(prize):
            return (
                f"Fallback triggered: pool limited to '{PROTECTED_GROUP}' members "
                f"(avoidance groups overridden)."
            )
        return prize.rule_description()

    def _update_fallback_state(self, prize, round_winners: List[User]) -> None:
        if any(self._is_drawer(prize, n) for n in FALLBACK_TRIGGER_DRAWERS):
            self.last_two_draw_results.append(
                any(is_protected_group(u.department) for u in round_winners)
            )
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif self._is_drawer(prize, FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []

    # ---------------------------------------------------------------- drawing
    def draw_one(self, prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self._rng.choice(pool)
        if winner.name in self.winner_names:
            return None
        self.winner_names.add(winner.name)
        self.result_manager.add_winner(winner, prize)
        return winner

    def run_round(
        self,
        prize,
        round_number: int = 1,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        interactive: bool = True,
    ) -> List[User]:
        output_func("")
        output_func(f"===== Round {round_number}: {prize.name} =====")
        output_func(f"Quantity: {prize.quantity}")
        output_func(f"Drawer: {prize.associated_drawer or '-'}")
        output_func(f"Rules: {self.describe_pool_rule(prize)}")

        round_winners: List[User] = []
        terminated = False
        for i in range(prize.quantity):
            if interactive:
                cmd = self._read(input_func,
                                 "Press Enter to draw, or type 'pause' / 'terminate': ")
                if cmd == "pause":
                    output_func("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                    while True:
                        c = self._read(input_func, "(paused) > ")
                        if c == "continue":
                            output_func("Lottery resumed.")
                            break
                        if c == "terminate":
                            terminated = True
                            break
                        output_func("Unknown command. Type 'continue' or 'terminate'.")
                elif cmd == "terminate":
                    terminated = True
            if terminated:
                output_func(f"Round terminated. Skipping remaining draws for {prize.name}.")
                break
            output_func(f"Currently drawing the {_ordinal(i + 1)} winner...")
            winner = self.draw_one(prize)
            if winner is None:
                output_func("No eligible participants remain for this prize. Round ends.")
                break
            round_winners.append(winner)
            output_func(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}"
            )

        self._update_fallback_state(prize, round_winners)
        output_func(f"--- Round {round_number} results ({prize.name}) ---")
        if round_winners:
            for idx, u in enumerate(round_winners, 1):
                output_func(f"{idx}. {u.name} ({u.department})")
        else:
            output_func("No winners in this round.")
        return round_winners

    @staticmethod
    def _read(input_func, prompt: str) -> str:
        try:
            return (input_func(prompt) or "").strip().lower()
        except EOFError:
            return ""
