"""Lottery rule engine and round execution."""

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User

SPECIAL_DRAWER = "Li Bin"
FALLBACK_WATCH_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru group"


def _norm(text) -> str:
    return " ".join(str(text or "").strip().lower().split())


def is_protected_group(department) -> bool:
    d = _norm(department)
    if d.endswith(" group"):
        d = d[:-len(" group")].strip()
    return d == "cheng ru"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    def __init__(self, users, rng: Optional[random.Random] = None):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self.rng = rng or random.Random()

    # ------------------------------------------------------------ rules
    def _is_winner(self, user) -> bool:
        return _norm(user.name) in self.winner_names

    def fallback_active(self, prize) -> bool:
        return (_norm(prize.associated_drawer) == _norm(FALLBACK_TARGET_DRAWER)
                and len(self.last_two_draw_results) >= 2
                and not any(self.last_two_draw_results[-2:]))

    def _get_eligible_pool(self, prize) -> List[User]:
        non_winners = [u for u in self.users if not self._is_winner(u)]
        if self.fallback_active(prize):
            protected = [u for u in non_winners if is_protected_group(u.department)]
            if protected:
                return protected
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return non_winners
        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in non_winners if _norm(u.department) not in avoid]

    def describe_rules(self, prize) -> str:
        lines = ["Previous winners are excluded (no repeated winning)."]
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            lines.append(f"Special drawer {SPECIAL_DRAWER}: relaxed filtering, "
                         "avoidance groups are ignored.")
        elif prize.avoid_groups:
            lines.append("Avoidance groups excluded: " + ", ".join(prize.avoid_groups))
        else:
            lines.append("No avoidance groups.")
        if self.fallback_active(prize):
            lines.append(f"Fallback active: pool limited to '{PROTECTED_GROUP}' "
                         "members (overrides avoidance).")
        return " ".join(lines)

    def mark_winner(self, user) -> None:
        self.winner_names.add(_norm(user.name))

    def draw_one(self, prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self.rng.choice(pool)
        self.mark_winner(user)
        return user

    def update_fallback_state(self, prize, winners) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in FALLBACK_WATCH_DRAWERS}:
            self.last_two_draw_results.append(
                any(is_protected_group(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []

    # ------------------------------------------------------------ rounds
    def run_round(self, prize: Prize,
                  input_func: Optional[Callable[[str], str]] = None,
                  output: Callable[[str], None] = print,
                  on_winner: Optional[Callable[[User, Prize], None]] = None):
        """Run one prize round. Returns (winners, terminated)."""
        output("=" * 60)
        output(f"Prize: {prize.name} | Quantity: {prize.quantity} | "
               f"Drawer: {prize.associated_drawer or 'None'}")
        output(f"Rules: {self.describe_rules(prize)}")
        output("=" * 60)
        winners: List[User] = []
        terminated = False
        paused = False
        for i in range(1, prize.quantity + 1):
            if input_func is not None:
                while True:
                    try:
                        prompt = ("[PAUSED] Type 'continue' or 'terminate': " if paused
                                  else f"[{i}/{prize.quantity}] Enter to draw, "
                                       "or 'pause'/'terminate': ")
                        cmd = input_func(prompt).strip().lower()
                    except EOFError:
                        cmd = "terminate"
                    if cmd == "terminate":
                        terminated = True
                        break
                    if paused:
                        if cmd == "continue":
                            paused = False
                            output("Lottery resumed.")
                            break
                        output("Lottery is paused.")
                    else:
                        if cmd in ("", "draw", "continue"):
                            break
                        if cmd == "pause":
                            paused = True
                            output("Lottery paused.")
                        else:
                            output(f"Unknown command: {cmd}")
            if terminated:
                output(f"Round '{prize.name}' terminated and skipped.")
                break
            output(f"Currently drawing the {ordinal(i)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output("No eligible candidates remain for this prize.")
                break
            winners.append(user)
            if on_winner:
                on_winner(user, prize)
            output(f"Congratulations {user.name} ({user.department}) "
                   f"for winning {prize.name}")
        self.update_fallback_state(prize, winners)
        output(f"--- Results of round '{prize.name}' ---")
        if winners:
            for n, u in enumerate(winners, 1):
                output(f"{n}. {u.name} ({u.department})")
        else:
            output("No winners in this round.")
        return winners, terminated
