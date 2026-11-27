"""Lottery rule engine and round execution."""

from __future__ import annotations

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def is_cheng_ru(department: str) -> bool:
    key = _norm(department).replace(" ", "").replace("_", "").replace("-", "")
    return "chengru" in key


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryManager:
    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ------------------------------------------------------------- rules
    def is_fallback_active(self, prize: Prize) -> bool:
        drawer = _norm(prize.associated_drawer or "")
        if drawer != _norm(FALLBACK_DRAWER):
            return False
        if len(self.last_two_draw_results) < 2:
            return False
        return not any(self.last_two_draw_results[-2:])

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        available = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            return [u for u in available if is_cheng_ru(u.department)]
        drawer = _norm(prize.associated_drawer or "")
        if drawer == _norm(SPECIAL_DRAWER):
            return available
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        if not avoid:
            return available
        preferred = [u for u in available if _norm(u.department) not in avoid]
        if preferred:
            return preferred
        # Avoidance group members remain eligible, but only after others.
        return [u for u in available if _norm(u.department) in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = []
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        if self.is_fallback_active(prize):
            parts.append(
                "Fallback active: prize pool limited to Cheng Ru group members"
            )
        elif _norm(prize.associated_drawer or "") == _norm(SPECIAL_DRAWER):
            parts.append("Special rule: only previous winners are excluded")
        else:
            if prize.avoid_groups:
                parts.append(
                    "Avoidance groups (drawn only after other members): "
                    + ", ".join(prize.avoid_groups)
                )
            parts.append("Previous winners are excluded")
        return "; ".join(parts)

    # ------------------------------------------------------------- drawing
    def mark_winner(self, user: User) -> bool:
        if user.name in self.winner_names:
            return False
        self.winner_names.add(user.name)
        self.winners.append(user)
        return True

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.mark_winner(user)
        return user

    def record_round_result(self, prize: Prize, round_winners: List[User]) -> None:
        if not prize.associated_drawer:
            return
        contains = any(is_cheng_ru(u.department) for u in round_winners)
        self.last_two_draw_results.append(contains)
        self.last_two_draw_results = self.last_two_draw_results[-2:]

    def run_round(
        self,
        prize: Prize,
        result_manager=None,
        input_func: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
    ) -> List[User]:
        output("")
        output(f"===== Prize: {prize.name} | Quantity: {prize.quantity} =====")
        output(f"Rules: {self.describe_rules(prize)}")
        output(
            "Commands: [Enter] draw next, 'pause' to pause, "
            "'continue' to resume, 'terminate' to end this round"
        )
        round_winners: List[User] = []
        i = 1
        terminated = False
        while i <= prize.quantity and not terminated:
            try:
                cmd = input_func(f"Ready to draw the {_ordinal(i)} winner > ")
            except EOFError:
                cmd = ""
            cmd = (cmd or "").strip().lower()
            if cmd == "terminate":
                output("Round terminated.")
                break
            if cmd == "pause":
                output("Lottery paused. Type 'continue' to resume or 'terminate' to end.")
                while True:
                    try:
                        c2 = input_func("(paused) > ")
                    except EOFError:
                        c2 = "continue"
                    c2 = (c2 or "").strip().lower()
                    if c2 == "continue":
                        output("Lottery resumed.")
                        break
                    if c2 == "terminate":
                        output("Round terminated.")
                        terminated = True
                        break
                    output("Paused. Please type 'continue' or 'terminate'.")
                continue
            if cmd not in ("", "continue", "draw"):
                output("Unknown command.")
                continue
            output(f"Currently drawing the {_ordinal(i)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output("No eligible participants left for this prize.")
                break
            if result_manager is not None:
                result_manager.add_winner(user, prize)
            round_winners.append(user)
            output(
                f"Congratulations {user.name} ({user.department}) "
                f"for winning {prize.name}"
            )
            i += 1
        self.record_round_result(prize, round_winners)
        output(f"--- Results of round '{prize.name}' ---")
        if not round_winners:
            output("  (no winners)")
        for n, u in enumerate(round_winners, 1):
            output(f"  {n}. {u.name} ({u.department})")
        return round_winners
