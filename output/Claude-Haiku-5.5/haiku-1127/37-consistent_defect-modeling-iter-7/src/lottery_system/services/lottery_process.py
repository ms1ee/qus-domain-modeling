"""Lottery process control: rounds, pause / continue / terminate and live display."""

from __future__ import annotations

import uuid


class LotteryProcess:
    """Runs the multi-round lottery and handles manual control commands."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

    def __init__(self, lottery_manager, result_manager, input_func=input, output_func=print):
        self.process_id = uuid.uuid4().hex[:8]
        self.state = self.IDLE
        self.current_round_number = 0
        self.round_statuses: list[str] = []
        self._lottery_manager = lottery_manager
        self._result_manager = result_manager
        self._input = input_func
        self._output = output_func

    def run(self, prizes) -> None:
        """Run one round per prize, in the given order."""
        if not prizes:
            self._output("No prizes configured. Nothing to draw.")
            return
        self.state = self.RUNNING
        for prize in prizes:
            self.current_round_number += 1
            self._run_round(prize)
        self.state = self.COMPLETED
        self._output("All lottery rounds completed.")

    def _run_round(self, prize) -> None:
        round_number = self.current_round_number
        self._output("")
        self._output(f"=== Round {round_number}: {prize.name} | Quantity: {prize.quantity} ===")
        self._output("Rules:")
        for rule in self._lottery_manager.describe_rules(prize):
            self._output(f"  - {rule}")

        round_winners = []
        terminated = False
        for position in range(1, prize.quantity + 1):
            if self._await_control() == "terminate":
                terminated = True
                self._output("Round terminated manually; remaining winners of this round are skipped.")
                break
            self._output(f"Currently drawing the {_ordinal(position)} winner...")
            user = self._lottery_manager.draw_winner(prize)
            if user is None:
                self._output("No eligible participants remain for this prize; the round ends.")
                break
            self._result_manager.add_winner(user, prize)
            round_winners.append(user)
            self._output(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.round_statuses.append("terminated" if terminated else "completed")
        self._output(f"Round {round_number} results ({len(round_winners)} winner(s), in winning order):")
        if not round_winners:
            self._output("  (no winners in this round)")
        for index, user in enumerate(round_winners, start=1):
            self._output(f"  {index}. {user.name} ({user.department})")

    def _await_control(self) -> str:
        """Wait for a control command before the next draw. Returns 'continue' or 'terminate'."""
        while True:
            command = self._input(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).strip().lower()
            if command in ("", "continue"):
                self.state = self.RUNNING
                return "continue"
            if command == "terminate":
                self.state = self.RUNNING
                return "terminate"
            if command == "pause":
                self.state = self.PAUSED
                self._output("Lottery paused.")
                return self._paused_loop()
            self._output("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _paused_loop(self) -> str:
        while True:
            command = self._input(
                "Type 'continue' to resume or 'terminate' to end this round: "
            ).strip().lower()
            if command == "continue":
                self.state = self.RUNNING
                self._output("Lottery resumed.")
                return "continue"
            if command == "terminate":
                self.state = self.RUNNING
                return "terminate"
            self._output("Unknown command. Use 'continue' or 'terminate'.")


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"
