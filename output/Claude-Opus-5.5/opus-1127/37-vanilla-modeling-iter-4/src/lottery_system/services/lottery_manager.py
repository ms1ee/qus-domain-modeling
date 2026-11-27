"""Lottery rule engine and round execution."""
import random
from typing import Callable, List, Optional

from lottery_system.models import (
    User, Prize, PROTECTED_GROUP, SPECIAL_DRAWER,
    FALLBACK_TRIGGER_PERSONS, FALLBACK_TARGET_PERSON,
)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _same_group(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


class LotteryManager:
    def __init__(self, users, result_manager=None):
        self.users: List[User] = list(users)
        self.winners = set()  # names of winners
        self.result_manager = result_manager
        if result_manager is not None:
            for w in result_manager.winners:
                self.winners.add(w.user.name)
        # results of the most recent trigger persons' rounds: True if contained protected group
        self.last_two_draw_results: List[bool] = []
        self.fallback_triggered = False
        self._rng = random.SystemRandom()

    # ---------- rule engine ----------
    def is_fallback_active(self, prize: Prize) -> bool:
        return (prize.associated_drawer == FALLBACK_TARGET_PERSON
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if u.name not in self.winners]
        if self.is_fallback_active(prize):
            self.fallback_triggered = True
            return [u for u in candidates if _same_group(u.department, PROTECTED_GROUP)]
        if prize.associated_drawer == SPECIAL_DRAWER:
            return candidates
        avoid = [g.strip().lower() for g in prize.avoid_groups]
        return [u for u in candidates if u.department.strip().lower() not in avoid]

    def get_rule_description(self, prize: Prize) -> str:
        if self.is_fallback_active(prize):
            return (f"Fallback active: {', '.join(FALLBACK_TRIGGER_PERSONS)} drew no "
                    f"'{PROTECTED_GROUP}' members, so the pool is limited to '{PROTECTED_GROUP}' "
                    f"members (avoidance groups ignored); previous winners excluded")
        if prize.associated_drawer == SPECIAL_DRAWER:
            return (f"Special drawer {SPECIAL_DRAWER}: only previous winners are excluded, "
                    f"avoidance groups are not applied")
        desc = "Previous winners excluded"
        if prize.avoid_groups:
            desc += f"; avoidance groups excluded: {', '.join(prize.avoid_groups)}"
        else:
            desc += "; no avoidance groups"
        return desc

    def record_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = prize.associated_drawer
        if drawer in FALLBACK_TRIGGER_PERSONS:
            contains = any(_same_group(u.department, PROTECTED_GROUP) for u in round_winners)
            self.last_two_draw_results.append(contains)
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == FALLBACK_TARGET_PERSON:
            self.last_two_draw_results = []

    # ---------- drawing ----------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winners.add(user.name)
        if self.result_manager is not None:
            self.result_manager.add_winner(user, prize)
        return user

    def run_round(self, prize: Prize, input_func: Callable[[str], str] = input,
                  output_func: Callable[[str], None] = print) -> List[User]:
        round_winners: List[User] = []
        terminated = False
        for i in range(prize.quantity):
            # command handling
            while True:
                cmd = self._read(input_func,
                                 f"[{prize.name}] Press Enter to draw, or type pause/terminate: ")
                if cmd in ("", "draw", "continue"):
                    break
                if cmd == "pause":
                    output_func("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                    while True:
                        c2 = self._read(input_func, "(paused) > ")
                        if c2 in ("continue", "terminate"):
                            break
                        output_func("Lottery is paused. Type 'continue' or 'terminate'.")
                    if c2 == "continue":
                        output_func("Lottery resumed.")
                        break
                    cmd = "terminate"
                if cmd == "terminate":
                    terminated = True
                    break
                output_func("Unknown command. Use Enter, 'pause', 'continue' or 'terminate'.")
            if terminated:
                output_func(f"Round for '{prize.name}' terminated; skipping remaining draws.")
                break
            output_func(f"Currently drawing the {_ordinal(i + 1)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output_func("No eligible participants remain for this prize. Round ends.")
                break
            round_winners.append(user)
            output_func(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        self.record_round(prize, round_winners)
        return round_winners

    @staticmethod
    def _read(input_func, prompt) -> str:
        try:
            return input_func(prompt).strip().lower()
        except EOFError:
            return "terminate"
