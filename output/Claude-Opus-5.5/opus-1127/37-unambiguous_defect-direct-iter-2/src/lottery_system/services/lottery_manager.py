"""Lottery rule engine and process control."""

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm_name(s: Optional[str]) -> str:
    return " ".join((s or "").strip().lower().split())


def _norm_group(s: Optional[str]) -> str:
    g = _norm_name(s)
    if g.endswith(" group"):
        g = g[: -len(" group")].strip()
    return g


def is_protected_group(department: str) -> bool:
    return _norm_group(department) == _norm_group(PROTECTED_GROUP)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryManager:
    def __init__(self, users, result_manager: Optional[ResultManager] = None, rng=None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.rng = rng or random.Random()
        self.winner_names = set()
        for w in self.result_manager.winners:
            self.winner_names.add(_norm_name(w.user.name))
        self.last_two_draw_results: List[bool] = []

    # ---------------- rule engine ----------------
    def _is_winner(self, user: User) -> bool:
        return _norm_name(user.name) in self.winner_names

    def fallback_active(self, prize: Prize) -> bool:
        return (
            _norm_name(prize.associated_drawer) == _norm_name(FALLBACK_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize) -> List[User]:
        candidates = [u for u in self.users if not self._is_winner(u)]
        if self.fallback_active(prize):
            protected = [u for u in candidates if is_protected_group(u.department)]
            if protected:
                return protected
        if _norm_name(prize.associated_drawer) == _norm_name(SPECIAL_DRAWER):
            return candidates
        avoid = {_norm_group(g) for g in (prize.avoid_groups or [])}
        return [u for u in candidates if _norm_group(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        desc = prize.rule_description()
        if _norm_name(prize.associated_drawer) == _norm_name(SPECIAL_DRAWER):
            desc += "; special rule: relaxed filtering (avoidance groups ignored)"
        if self.fallback_active(prize):
            desc += f"; fallback active: pool limited to '{PROTECTED_GROUP}' members"
        return desc

    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        while pool:
            user = self.rng.choice(pool)
            if self.result_manager.add_winner(user, prize):
                self.winner_names.add(_norm_name(user.name))
                return user
            self.winner_names.add(_norm_name(user.name))
            pool = [u for u in pool if u is not user and not self._is_winner(u)]
        return None

    def record_round(self, prize: Prize, round_winners: List[User]) -> None:
        drawer = _norm_name(prize.associated_drawer)
        watched = {_norm_name(d) for d in FALLBACK_WATCHED_DRAWERS}
        if drawer in watched:
            self.last_two_draw_results.append(any(is_protected_group(u.department) for u in round_winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        else:
            self.last_two_draw_results = []

    # ---------------- process control ----------------
    def run_round(self, prize: Prize, round_no: int = 1, total_rounds: int = 1,
                  input_func: Callable[[str], str] = input,
                  output: Callable[[str], None] = print) -> List[User]:
        output("")
        output("=" * 60)
        output(f"Round {round_no}/{total_rounds}: {prize.name}")
        output(f"Quantity: {prize.quantity}")
        output(f"Rules: {self.describe_rules(prize)}")
        output("=" * 60)
        round_winners: List[User] = []
        auto = False
        k = 0
        while k < prize.quantity:
            if not auto:
                try:
                    cmd = input_func(
                        "Press Enter to draw (commands: pause / continue / terminate / auto): "
                    ).strip().lower()
                except EOFError:
                    cmd = "auto"
                if cmd == "pause":
                    output("Lottery paused. Input 'continue' to resume or 'terminate' to skip this round.")
                    while True:
                        try:
                            c = input_func("[Paused] > ").strip().lower()
                        except EOFError:
                            c = "continue"
                        if c in ("continue", "terminate"):
                            break
                        output("Lottery is paused. Input 'continue' or 'terminate'.")
                    if c == "terminate":
                        output(f"Round '{prize.name}' terminated.")
                        break
                    output("Lottery resumed.")
                    continue
                if cmd == "terminate":
                    output(f"Round '{prize.name}' terminated.")
                    break
                if cmd == "auto":
                    auto = True
                elif cmd not in ("", "continue"):
                    output(f"Unknown command: {cmd}")
                    continue
            output(f"Currently drawing the {ordinal(k + 1)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output("No eligible participants remain for this prize. Round ends early.")
                break
            round_winners.append(user)
            output(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            k += 1
        self.record_round(prize, round_winners)
        output(f"--- Results of round '{prize.name}' ---")
        if round_winners:
            for i, u in enumerate(round_winners, 1):
                output(f"{i}. {u.name} ({u.department})")
        else:
            output("No winners in this round.")
        return round_winners

    def run_all(self, prizes, input_func=input, output=print):
        prizes = list(prizes)
        results = {}
        for i, prize in enumerate(prizes, 1):
            results[prize.name] = self.run_round(prize, i, len(prizes), input_func, output)
        return results
