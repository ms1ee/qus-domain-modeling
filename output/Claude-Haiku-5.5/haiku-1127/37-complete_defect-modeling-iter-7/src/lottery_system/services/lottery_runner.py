"""Runs lottery rounds with pause / continue / terminate control and live display."""

from __future__ import annotations

import time
from typing import Callable

from ..models import Prize, User
from .lottery_manager import LotteryManager
from .result_manager import ResultManager, Winner


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryRunner:
    def __init__(self, lottery: LotteryManager, result_manager: ResultManager,
                 console, output: Callable[[str], None] = print,
                 draw_delay: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.lottery = lottery
        self.result_manager = result_manager
        self.console = console
        self.output = output
        self.draw_delay = draw_delay
        self.sleep = sleep

    def _say(self, message: str = "") -> None:
        self.output(message)

    def run(self, prizes: list[Prize]) -> list[Winner]:
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self.run_round(index, total, prize)
        self._say("\nAll lottery rounds completed.")
        return self.result_manager.get_all_winners()

    def _process_commands(self, paused: bool) -> tuple[bool, bool]:
        """Handle pending control commands. Returns (paused, terminated)."""
        while True:
            # While paused, block until a command arrives; otherwise poll.
            command = self.console.get() if paused else self.console.poll()
            command = command.strip().lower()
            if not command:
                if paused:
                    continue
                return paused, False
            if command == "pause":
                if paused:
                    self._say("Lottery is already paused.")
                else:
                    paused = True
                    self._say("[PAUSED] Type 'continue' to resume or 'terminate' to skip this round.")
            elif command == "continue":
                if paused:
                    paused = False
                    self._say("Lottery resumed.")
                else:
                    self._say("Lottery is not paused.")
            elif command == "terminate":
                self._say("Terminating the current round...")
                return paused, True
            else:
                self._say(f"Unknown command '{command}'. Use: pause, continue, terminate")

    def run_round(self, index: int, total: int, prize: Prize) -> list[User]:
        self._say("")
        self._say(f"===== Round {index}/{total}: {prize.name} =====")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Associated lottery person: {prize.associated_drawer or 'None'}")
        self._say(f"Rules: {self.lottery.describe_rules(prize)}")
        self._say("Controls: pause | continue | terminate")

        round_winners: list[User] = []
        paused = False
        terminated = False
        draw_no = 0

        while draw_no < prize.quantity:
            paused, terminated = self._process_commands(paused)
            if terminated:
                break

            next_no = draw_no + 1
            self._say(f"Currently drawing the {ordinal(next_no)} winner...")
            self.sleep(self.draw_delay)

            winner = self.lottery.draw_winner(prize)
            if winner is None:
                self._say("No eligible participants remain for this prize. Round ends early.")
                break

            draw_no = next_no
            self.result_manager.add_winner(winner, prize)
            round_winners.append(winner)
            self._say(f"Congratulations {winner.name} ({winner.department}) "
                      f"for winning {prize.name}")

        self.lottery.finish_round(prize, round_winners)

        self._say(f"Round {index} finished: {len(round_winners)}/{prize.quantity} winner(s).")
        for position, user in enumerate(round_winners, start=1):
            self._say(f"  {position}. {user.name} ({user.department})")
        return round_winners
