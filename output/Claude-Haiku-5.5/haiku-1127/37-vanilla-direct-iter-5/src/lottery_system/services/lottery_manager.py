import random

from lottery_system.models import Prize, User
from lottery_system.services.result_manager import ResultManager


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryManager:
    """Runs lottery rounds and applies the lottery rule engine."""

    CHENG_RU_GROUP = "Cheng Ru Group"
    NO_AVOIDANCE_DRAWER = "Li Bin"
    FALLBACK_DRAWER = "Ma Jiaqi"
    HISTORY_DRAWERS = ("Chen Qixian", "Jin Duo")

    def __init__(self, users):
        self.users: list[User] = list(users)
        self.result_manager = ResultManager()
        # Each entry: whether that lottery person's round produced a Cheng Ru Group winner.
        self.last_two_draw_results: list[bool] = []
        self._winner_names: set[str] = set()
        self._rng = random.SystemRandom()

    def has_won(self, user: User) -> bool:
        return user.name in self._winner_names

    def _is_fallback_active(self, prize: Prize) -> bool:
        return (
            prize.associated_drawer == self.FALLBACK_DRAWER
            and len(self.last_two_draw_results) == 2
            and not any(self.last_two_draw_results)
        )

    def _get_eligible_pool(self, prize: Prize) -> list[User]:
        candidates = [u for u in self.users if u.name not in self._winner_names]
        if self._is_fallback_active(prize):
            # Fallback protection overrides avoidance groups.
            return [u for u in candidates if u.department == self.CHENG_RU_GROUP]
        if prize.associated_drawer == self.NO_AVOIDANCE_DRAWER:
            return candidates
        avoid = set(prize.avoid_groups)
        return [u for u in candidates if u.department not in avoid]

    def describe_rules(self, prize: Prize) -> str:
        parts: list[str] = []
        if prize.associated_drawer == self.NO_AVOIDANCE_DRAWER:
            parts.append("previous winners are excluded; avoidance groups are not applied")
        elif self._is_fallback_active(prize):
            parts.append("Cheng Ru Group protection active: only Cheng Ru Group members are eligible")
        else:
            parts.append("previous winners are excluded")
            if prize.avoid_groups:
                parts.append("avoidance groups: " + ", ".join(prize.avoid_groups))
        if prize.associated_drawer:
            parts.append(f"lottery person: {prize.associated_drawer}")
        return "; ".join(parts)

    def draw_one(self, prize: Prize):
        pool = self._get_eligible_pool(prize)
        if not pool:
            return None
        user = self._rng.choice(pool)
        self._winner_names.add(user.name)
        self.result_manager.add_winner(user, prize)
        return user

    def record_round_completion(self, prize: Prize, round_winners: list[User]) -> None:
        if prize.associated_drawer in self.HISTORY_DRAWERS:
            got_cheng_ru = any(u.department == self.CHENG_RU_GROUP for u in round_winners)
            self.last_two_draw_results = (self.last_two_draw_results + [got_cheng_ru])[-2:]
        elif prize.associated_drawer == self.FALLBACK_DRAWER and self._is_fallback_active(prize):
            # The protection has been applied; start a fresh history.
            self.last_two_draw_results = []

    def _wait_while_paused(self, input_func, output_func) -> str:
        output_func("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = input_func("(paused) > ").strip().lower()
            if command in ("continue", "terminate"):
                return command
            output_func("Unknown command. Use 'continue' or 'terminate'.")

    def run_round(self, prize: Prize, input_func=input, output_func=print) -> list[User]:
        output_func("")
        output_func(
            f"=== Current round: {prize.name} | Quantity: {prize.quantity} | "
            f"Lottery person: {prize.associated_drawer or 'None'}"
        )
        output_func(f"Rule: {self.describe_rules(prize)}")

        round_winners: list[User] = []
        terminated = False
        while len(round_winners) < prize.quantity:
            if not self._get_eligible_pool(prize):
                output_func("No eligible candidates remain; this round ends early.")
                break

            command = input_func(
                f"[Enter] draw the {_ordinal(len(round_winners) + 1)} winner | "
                f"'pause' | 'terminate' > "
            ).strip().lower()

            if command == "pause":
                command = self._wait_while_paused(input_func, output_func)
                if command == "continue":
                    command = ""

            if command == "terminate":
                terminated = True
                output_func("Round terminated by operator; skipping remaining draws.")
                break
            if command not in ("", "continue"):
                output_func(f"Unknown command '{command}'.")
                continue

            position = len(round_winners) + 1
            output_func(f"Currently drawing the {_ordinal(position)} winner...")
            user = self.draw_one(prize)
            if user is None:
                output_func("No eligible candidates remain; this round ends early.")
                break
            round_winners.append(user)
            output_func(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.record_round_completion(prize, round_winners)

        output_func(f"Round finished: {len(round_winners)}/{prize.quantity} winner(s) for {prize.name}.")
        if round_winners:
            output_func("Round results:")
            for idx, user in enumerate(round_winners, start=1):
                output_func(f"  {idx}. {user.name} ({user.department})")
        if terminated:
            output_func("This round was terminated early.")
        return round_winners
