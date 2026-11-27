"""Lottery rule engine and process control."""
import random
from typing import Callable, List, Optional

from lottery_system.models import (FALLBACK_DRAWER, MONITORED_DRAWERS, PROTECTED_GROUP,
                                   SPECIAL_DRAWER, Prize, User, normalize)
from lottery_system.services.result_manager import ResultManager


class LotteryManager:
    def __init__(self, users, result_manager: Optional[ResultManager] = None):
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winners = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = random.Random()

    # ---- rule engine ----
    def _is_winner(self, user) -> bool:
        return user.name in self.winners or self.result_manager.has_winner(user)

    def _non_winners(self) -> List[User]:
        return [u for u in self.users if not self._is_winner(u)]

    def _fallback_active(self, prize) -> bool:
        return (normalize(prize.associated_drawer) == normalize(FALLBACK_DRAWER)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize) -> List[User]:
        candidates = self._non_winners()
        if self._fallback_active(prize):
            protected = [u for u in candidates
                         if normalize(u.department) == normalize(PROTECTED_GROUP)]
            if protected:
                return protected
        if normalize(prize.associated_drawer) == normalize(SPECIAL_DRAWER):
            return candidates
        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in candidates if normalize(u.department) not in avoid]

    def _get_deferred_pool(self, prize) -> List[User]:
        """Avoidance-group members, drawn only after all other members are exhausted."""
        avoid = {normalize(g) for g in prize.avoid_groups}
        return [u for u in self._non_winners() if normalize(u.department) in avoid]

    def get_rule_mode(self, prize) -> str:
        if self._fallback_active(prize):
            return f"FALLBACK: pool limited to '{PROTECTED_GROUP}' members"
        return prize.rule_description()

    # ---- drawing ----
    def draw_one(self, prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            pool = self._get_deferred_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.winners.add(user.name)
        self.result_manager.add_winner(user, prize)
        return user

    def _finish_round(self, prize, round_winners):
        drawer = normalize(prize.associated_drawer)
        if drawer in {normalize(d) for d in MONITORED_DRAWERS}:
            hit = any(normalize(u.department) == normalize(PROTECTED_GROUP)
                      for u in round_winners)
            self.last_two_draw_results.append(hit)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == normalize(FALLBACK_DRAWER):
            self.last_two_draw_results = []

    def draw_prize(self, prize) -> List[User]:
        round_winners = []
        for _ in range(prize.quantity):
            u = self.draw_one(prize)
            if u is None:
                break
            round_winners.append(u)
        self._finish_round(prize, round_winners)
        return round_winners

    def run_round(self, prize, round_number: int = 1,
                  input_func: Callable[[str], str] = input,
                  output: Callable[[str], None] = print) -> List[User]:
        output(f"\n===== Round {round_number}: {prize.name} =====")
        output(f"Quantity: {prize.quantity}")
        output(f"Rules: {self.get_rule_mode(prize)}")
        output("Commands: [Enter] draw next, 'pause', 'continue', 'terminate'")
        round_winners: List[User] = []
        i = 0
        paused = False
        while i < prize.quantity:
            try:
                cmd = input_func("Paused> " if paused else
                                 f"Draw #{i + 1} (Enter/pause/terminate)> ").strip().lower()
            except EOFError:
                cmd = "terminate"
            if cmd == "terminate":
                output("Current round terminated, skipping remaining draws.")
                break
            if cmd == "pause":
                paused = True
                output("Lottery paused. Type 'continue' to resume or 'terminate' to end round.")
                continue
            if cmd == "continue":
                if paused:
                    paused = False
                    output("Lottery resumed.")
                continue
            if paused:
                output("Lottery is paused. Type 'continue' or 'terminate'.")
                continue
            if cmd not in ("", "draw", "d"):
                output("Unknown command.")
                continue
            output(f"Currently drawing the {i + 1}th winner...")
            user = self.draw_one(prize)
            if user is None:
                output("No eligible participants left for this prize.")
                break
            round_winners.append(user)
            output(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            i += 1
        self._finish_round(prize, round_winners)
        output(f"--- Round {round_number} results ({prize.name}) ---")
        if not round_winners:
            output("(no winners)")
        for n, u in enumerate(round_winners, 1):
            output(f"{n}. {u.name} ({u.department})")
        return round_winners
