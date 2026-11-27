"""Lottery rule engine and round control."""

import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User

CHENG_RU_GROUP = "Cheng Ru group"
RELAXED_DRAWER = "Li Bin"
FALLBACK_WATCH_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def _norm(s) -> str:
    return " ".join(str(s or "").split()).lower()


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    def __init__(self, users):
        self.users: List[User] = list(users)
        self.winner_names = set()
        self.winners: List[User] = []
        self.last_two_draw_results: List[bool] = []
        self._rng = random.Random()

    # ---- rule helpers ----
    @staticmethod
    def _is_cheng_ru(user: User) -> bool:
        return _norm(user.department) == _norm(CHENG_RU_GROUP)

    def _fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(FALLBACK_TARGET_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        not_won = [u for u in self.users if u.name not in self.winner_names]

        if self._fallback_active(prize):
            forced = [u for u in not_won if self._is_cheng_ru(u)]
            if forced:
                return forced
            # No Cheng Ru members left; fall through to normal rules.

        if _norm(prize.associated_drawer) == _norm(RELAXED_DRAWER):
            # Relaxed rules: avoidance groups are not applied.
            return not_won

        avoid = {_norm(g) for g in (prize.avoid_groups or [])}
        return [u for u in not_won if _norm(u.department) not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        if _norm(prize.associated_drawer) == _norm(RELAXED_DRAWER) and not self._fallback_active(prize):
            parts.append(f"special drawer {RELAXED_DRAWER}: relaxed filtering "
                         f"(avoidance groups ignored)")
        elif prize.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(prize.avoid_groups))
        if self._fallback_active(prize):
            parts.append(f"fallback active: pool limited to '{CHENG_RU_GROUP}' members")
        return "; ".join(parts)

    def _record_winner(self, user: User) -> bool:
        if user.name in self.winner_names:
            return False
        self.winner_names.add(user.name)
        self.winners.append(user)
        return True

    def _update_fallback_state(self, prize: Prize, results: List[User]) -> None:
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in FALLBACK_WATCH_DRAWERS}:
            self.last_two_draw_results.append(any(self._is_cheng_ru(u) for u in results))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(FALLBACK_TARGET_DRAWER):
            self.last_two_draw_results = []

    # ---- drawing ----
    def draw(self, prize: Prize, result_manager=None) -> List[User]:
        """Non-interactive draw of a full round."""
        return self.run_round(prize, result_manager=result_manager,
                              interactive=False, output_func=lambda *a, **k: None)

    def run_round(self, prize: Prize, result_manager=None,
                  input_func: Callable[[str], str] = input,
                  output_func: Callable[..., None] = print,
                  interactive: bool = True) -> List[User]:
        output_func("")
        output_func("=" * 60)
        output_func(f"Prize: {prize.name} | Quantity: {prize.quantity}"
                    f" | Drawer: {prize.associated_drawer or 'N/A'}")
        output_func(f"Rules: {self.describe_rules(prize)}")
        output_func("=" * 60)

        results: List[User] = []
        terminated = False
        while len(results) < prize.quantity:
            pool = self._get_eligible_pool(prize)
            if not pool:
                output_func("No eligible candidates remaining for this prize.")
                break
            n = len(results) + 1
            if interactive:
                cmd = self._safe_input(
                    input_func,
                    f"[Enter] draw {_ordinal(n)} winner | 'pause' | 'terminate': ")
                if cmd == "pause":
                    output_func("Lottery paused.")
                    while True:
                        cmd2 = self._safe_input(
                            input_func, "Paused. Type 'continue' to resume or 'terminate': ")
                        if cmd2 == "continue":
                            output_func("Lottery resumed.")
                            break
                        if cmd2 == "terminate":
                            terminated = True
                            break
                        output_func("Unknown command while paused.")
                elif cmd == "terminate":
                    terminated = True
                if terminated:
                    output_func(f"Round '{prize.name}' terminated and skipped.")
                    break
                # pool may be stale only if state changed; recompute to be safe
                pool = self._get_eligible_pool(prize)
                if not pool:
                    output_func("No eligible candidates remaining for this prize.")
                    break
            output_func(f"Currently drawing the {_ordinal(n)} winner...")
            winner = self._rng.choice(pool)
            if not self._record_winner(winner):
                continue
            if result_manager is not None:
                result_manager.add_winner(winner, prize)
            results.append(winner)
            output_func(f"Congratulations {winner.name} ({winner.department}) "
                        f"for winning {prize.name}")

        self._update_fallback_state(prize, results)

        output_func("-" * 60)
        output_func(f"Round results for {prize.name}:")
        if results:
            for i, u in enumerate(results, 1):
                output_func(f"  {i}. {u.name} ({u.department})")
        else:
            output_func("  (no winners)")
        return results

    @staticmethod
    def _safe_input(input_func, prompt: str) -> str:
        try:
            return (input_func(prompt) or "").strip().lower()
        except EOFError:
            return "terminate"
