"""Lottery process control: rounds, pause / continue / terminate and live display."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from lottery_system.constants import CHENG_RU_GROUP, CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager

CMD_DRAW = "draw"
CMD_PAUSE = "pause"
CMD_CONTINUE = "continue"
CMD_TERMINATE = "terminate"

STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_RUNNING = "RUNNING"
STATUS_PAUSED = "PAUSED"
STATUS_COMPLETED = "COMPLETED"


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def describe_rules(prize: Prize) -> str:
    rules = ["Previous winners are excluded"]
    drawer = prize.associated_drawer
    if drawer == LI_BIN:
        rules.append("Special rule for Li Bin: only previous winners are filtered (avoidance groups not applied)")
    elif prize.avoid_groups:
        rules.append(
            "Members of avoidance groups ("
            + ", ".join(prize.avoid_groups)
            + ") are drawn only after other members"
        )
    if drawer == MA_JIAQI:
        rules.append(
            "Cheng Ru group protection: if the last two draws by "
            f"{CHEN_QIXIAN}/{JIN_DUO} had no {CHENG_RU_GROUP} winners, "
            f"this draw is limited to {CHENG_RU_GROUP} members"
        )
    if drawer:
        rules.append(f"Lottery person: {drawer}")
    return "; ".join(rules)


class LotteryProcess:
    def __init__(
        self,
        users: list[User],
        prizes: list[Prize],
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self.status: str = STATUS_NOT_STARTED
        self.current_round_index: int = 0
        self.start_time: datetime | None = None
        self.commands: list[tuple[str, datetime]] = []
        self.prizes: list[Prize] = list(prizes)
        self.lottery = LotteryManager(users)
        self.results = ResultManager()
        self._ask = input_func
        self._say = output_func

    def run(self) -> ResultManager:
        self.status = STATUS_RUNNING
        self.start_time = datetime.now()
        for index, prize in enumerate(self.prizes, start=1):
            self.current_round_index = index
            self._run_round(index, prize)
        self.status = STATUS_COMPLETED
        return self.results

    def _run_round(self, index: int, prize: Prize) -> None:
        self._say("")
        self._say(f"=== Round {index}: {prize.name} ===")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rules: {describe_rules(prize)}")
        round_winners: list[User] = []
        drawn = 0
        while drawn < prize.quantity:
            action = self._await_action()
            if action == CMD_TERMINATE:
                self._say("Round terminated; skipping to the next round.")
                break
            position = drawn + 1
            self._say(f"Currently drawing the {ordinal(position)} winner...")
            winner = self.lottery.draw_one(prize)
            if winner is None:
                self._say("No eligible participants remain for this prize. Round ends.")
                break
            self.results.add_winner(winner, prize)
            round_winners.append(winner)
            drawn += 1
            self._say(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")
        self._say(f"Round {index} results:")
        if not round_winners:
            self._say("  (no winners)")
        for position, user in enumerate(round_winners, start=1):
            self._say(f"  {position}. {user.name} ({user.department})")

    def _await_action(self) -> str:
        while True:
            command = self._ask(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).strip().lower()
            if command == "":
                return CMD_DRAW
            if command == CMD_TERMINATE:
                self._record(CMD_TERMINATE)
                return CMD_TERMINATE
            if command == CMD_CONTINUE:
                self._say("Lottery is not paused.")
                continue
            if command == CMD_PAUSE:
                self._record(CMD_PAUSE)
                self.status = STATUS_PAUSED
                self._say("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("> ").strip().lower()
                    if resume == CMD_CONTINUE:
                        self._record(CMD_CONTINUE)
                        self.status = STATUS_RUNNING
                        self._say("Lottery resumed.")
                        break
                    if resume == CMD_TERMINATE:
                        self._record(CMD_TERMINATE)
                        self.status = STATUS_RUNNING
                        return CMD_TERMINATE
                    self._say("Lottery is paused. Type 'continue' or 'terminate'.")
                continue
            self._say("Unknown command. Press Enter to draw, or type 'pause' / 'terminate'.")

    def _record(self, command: str) -> None:
        self.commands.append((command, datetime.now()))
