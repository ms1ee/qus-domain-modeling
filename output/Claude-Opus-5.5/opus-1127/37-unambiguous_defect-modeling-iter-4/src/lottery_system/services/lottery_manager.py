"""Lottery process control and rule engine."""

from __future__ import annotations

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager


def _norm(text: Optional[str]) -> str:
    return " ".join(str(text or "").lower().split())


def _norm_group(text: Optional[str]) -> str:
    t = _norm(text)
    if t.endswith(" group"):
        t = t[: -len(" group")].strip()
    return t


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    """Rule engine + round execution."""

    PROTECTED_GROUP = "Cheng Ru group"
    RELAXED_DRAWER = "Li Bin"
    FALLBACK_TRIGGERS = ("Chen Qixian", "Jin Duo")
    FALLBACK_TARGET = "Ma Jiaqi"

    def __init__(self, users, result_manager: Optional[ResultManager] = None, rng=None):
        self.users: List[User] = list(users or [])
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = {w.user.name for w in self.result_manager.get_winners()}
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.SystemRandom()
        self.round_number = 0

    # ------------------------------------------------------------ rule helpers
    def is_protected_member(self, user: User) -> bool:
        return _norm_group(user.department) == _norm_group(self.PROTECTED_GROUP)

    def is_relaxed(self, prize: Prize) -> bool:
        return _norm(prize.associated_drawer) == _norm(self.RELAXED_DRAWER)

    def is_fallback_active(self, prize: Prize) -> bool:
        if _norm(prize.associated_drawer) != _norm(self.FALLBACK_TARGET):
            return False
        recent = self.last_two_draw_results[-2:]
        return len(recent) >= 2 and not any(recent)

    def _has_won(self, user: User) -> bool:
        return user.name in self.winner_names or self.result_manager.has_won(user.name)

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        base = [u for u in self.users if not self._has_won(u)]
        if self.is_fallback_active(prize):
            protected = [u for u in base if self.is_protected_member(u)]
            if protected:
                return protected
        if self.is_relaxed(prize):
            return base
        avoid = {_norm_group(g) for g in prize.avoid_groups}
        return [u for u in base if _norm_group(u.department) not in avoid]

    def get_rule_description(self, prize: Prize) -> str:
        rules = ["previous winners excluded"]
        if self.is_fallback_active(prize):
            rules.append(
                f"FALLBACK ACTIVE: pool limited to '{self.PROTECTED_GROUP}' members "
                f"(Cheng Ru group protection)"
            )
        elif self.is_relaxed(prize):
            rules.append(f"relaxed rules for drawer {self.RELAXED_DRAWER}: avoidance groups ignored")
        elif prize.avoid_groups:
            rules.append("avoidance groups: " + ", ".join(prize.avoid_groups))
        else:
            rules.append("no avoidance groups")
        if prize.associated_drawer:
            rules.append(f"drawer: {prize.associated_drawer}")
        return "; ".join(rules)

    # ---------------------------------------------------------------- drawing
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        winner = self.rng.choice(pool)
        if not self.result_manager.add_winner(winner, prize):
            # Should not happen: pool excludes winners. Guard anyway.
            self.winner_names.add(winner.name)
            return None
        self.winner_names.add(winner.name)
        return winner

    def finish_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        triggers = {_norm(t) for t in self.FALLBACK_TRIGGERS}
        if drawer in triggers:
            self.last_two_draw_results.append(
                any(self.is_protected_member(u) for u in round_winners)
            )
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []

    def run_round(
        self,
        prize: Prize,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> List[User]:
        self.round_number += 1
        output_func("")
        output_func("=" * 60)
        output_func(f"Round {self.round_number}: {prize.name}")
        output_func(f"Quantity: {prize.quantity}")
        output_func(f"Rules: {self.get_rule_description(prize)}")
        output_func("=" * 60)
        output_func("Commands: [Enter]=draw next, 'auto'=draw all remaining, "
                    "'pause', 'continue', 'terminate'")
        round_winners: List[User] = []
        auto = False
        paused = False
        terminated = False
        i = 0
        while i < prize.quantity:
            if not auto:
                try:
                    cmd = _norm(input_func(
                        "(paused) > " if paused
                        else f"Draw {ordinal(i + 1)} winner > "
                    ))
                except EOFError:
                    cmd = "terminate"
                if cmd == "terminate":
                    terminated = True
                    output_func("Current round terminated and skipped.")
                    break
                if cmd == "pause":
                    paused = True
                    output_func("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                    continue
                if paused:
                    if cmd == "continue":
                        paused = False
                        output_func("Lottery resumed.")
                    else:
                        output_func("Lottery is paused. Type 'continue' or 'terminate'.")
                    continue
                if cmd == "continue":
                    output_func("Lottery is not paused.")
                    continue
                if cmd == "auto":
                    auto = True
                elif cmd != "":
                    output_func(f"Unknown command: {cmd}")
                    continue
            output_func(f"Currently drawing the {ordinal(i + 1)} winner...")
            winner = self.draw_one(prize)
            if winner is None:
                output_func("No eligible participants remain for this prize. Round ends early.")
                break
            round_winners.append(winner)
            output_func(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}"
            )
            i += 1
        self.finish_round(prize, round_winners)
        output_func("-" * 60)
        status = "terminated" if terminated else "completed"
        output_func(f"Round {self.round_number} {status}. Results ({len(round_winners)}/{prize.quantity}):")
        if round_winners:
            for n, u in enumerate(round_winners, start=1):
                output_func(f"  {n}. {u.name} ({u.department}) - {prize.name}")
        else:
            output_func("  No winners in this round.")
        return round_winners
