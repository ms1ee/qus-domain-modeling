import random
from typing import Callable, List, Optional

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager

SPECIAL_DRAWER = "Li Bin"
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
PROTECTED_DRAWER = "Ma Jiaqi"


def is_cheng_ru(department: str) -> bool:
    return "chengru" in department.lower().replace(" ", "").replace("_", "").replace("-", "")


def _norm(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    def __init__(self, users, result_manager: Optional[ResultManager] = None):
        self.users: List[User] = list(users)
        self.result_manager = result_manager if result_manager is not None else ResultManager()
        self.winner_names = set()
        self.last_two_draw_results: List[bool] = []
        self._rng = random.SystemRandom()

    # ---------- rules ----------
    def is_fallback_active(self, prize: Prize) -> bool:
        return (
            _norm(prize.associated_drawer) == _norm(PROTECTED_DRAWER)
            and len(self.last_two_draw_results) >= 2
            and not any(self.last_two_draw_results[-2:])
        )

    def _get_eligible_pool(self, prize: Prize) -> List[User]:
        candidates = [u for u in self.users if u.name not in self.winner_names]
        if self.is_fallback_active(prize):
            cheng = [u for u in candidates if is_cheng_ru(u.department)]
            if cheng:
                return cheng
        if _norm(prize.associated_drawer) == _norm(SPECIAL_DRAWER):
            return candidates
        avoid = {g.strip() for g in (prize.avoid_groups or [])}
        non_avoid = [u for u in candidates if u.department.strip() not in avoid]
        if non_avoid:
            return non_avoid
        # avoided members remain eligible, drawn after all others
        return [u for u in candidates if u.department.strip() in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts = ["Previous winners are excluded"]
        drawer = prize.associated_drawer
        if self.is_fallback_active(prize):
            parts.append(
                f"Cheng Ru group protection active: prize pool limited to Cheng Ru group members "
                f"(drawer {drawer})"
            )
        elif _norm(drawer) == _norm(SPECIAL_DRAWER):
            parts.append(f"Special drawer {drawer}: avoidance groups not applied")
        elif prize.avoid_groups:
            parts.append(
                "Avoidance groups (drawn only after all other members): "
                + ", ".join(prize.avoid_groups)
            )
        else:
            parts.append("No avoidance groups")
        if drawer:
            parts.append(f"Lottery person: {drawer}")
        return "; ".join(parts)

    # ---------- drawing ----------
    def draw_one(self, prize: Prize) -> Optional[User]:
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self.winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)
        return user

    def _update_tracking(self, prize: Prize, winners: List[User]):
        drawer = _norm(prize.associated_drawer)
        if drawer in {_norm(d) for d in WATCHED_DRAWERS}:
            self.last_two_draw_results.append(any(is_cheng_ru(u.department) for u in winners))
            self.last_two_draw_results = self.last_two_draw_results[-2:]
        elif drawer == _norm(PROTECTED_DRAWER):
            self.last_two_draw_results = []

    def run_round(self, prize: Prize, input_func: Callable = input,
                  output_func: Callable = print) -> List[User]:
        output_func("=" * 50)
        output_func(f"Current prize: {prize.name}")
        output_func(f"Quantity: {prize.quantity}")
        output_func(f"Rules: {self.describe_rules(prize)}")
        output_func("Commands: [Enter]=draw, 'pause', 'continue', 'terminate'")
        output_func("=" * 50)
        winners: List[User] = []
        terminated = False
        for i in range(1, prize.quantity + 1):
            while True:
                try:
                    cmd = input_func(f"Press Enter to draw the {ordinal(i)} winner > ").strip().lower()
                except EOFError:
                    cmd = ""
                if cmd in ("", "draw", "continue"):
                    break
                if cmd == "terminate":
                    terminated = True
                    break
                if cmd == "pause":
                    output_func("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                    while True:
                        try:
                            c = input_func("(paused) > ").strip().lower()
                        except EOFError:
                            c = "terminate"
                        if c == "continue":
                            output_func("Lottery resumed.")
                            break
                        if c == "terminate":
                            terminated = True
                            break
                        output_func("Lottery is paused. Type 'continue' or 'terminate'.")
                    break
                output_func("Unknown command. Use Enter, 'pause', 'continue' or 'terminate'.")
            if terminated:
                output_func(f"Round '{prize.name}' terminated and skipped.")
                break
            output_func(f"Currently drawing the {ordinal(i)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output_func("No eligible participants remain for this prize.")
                break
            winners.append(user)
            output_func(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        self._update_tracking(prize, winners)
        output_func("-" * 50)
        output_func(f"Round results for {prize.name}:")
        if winners:
            for n, u in enumerate(winners, 1):
                output_func(f"  {n}. {u.name} ({u.department})")
        else:
            output_func("  No winners in this round.")
        return winners
