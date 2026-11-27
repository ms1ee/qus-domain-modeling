"""Command-line interface: menus, lottery process control and result display."""
from __future__ import annotations

import queue
import sys
import threading
import time
from typing import TextIO

from lottery_system.models import Prize, User, sort_prizes_by_level
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

EOF_TOKEN = "__EOF__"
DRAWER_OPTIONS = ["Chen Qixian", "Jin Duo", "Ma Jiaqi", "Li Bin"]

BANNER = "=" * 50 + "\n   Smart Lottery System - Team Building Event\n" + "=" * 50
MAIN_MENU = """
--- Main Menu ---
1. Load participant list
2. View department groups
3. Prize configuration
4. Start lottery
5. Show winner list
6. Export winner list (CSV txt)
0. Exit"""
PRIZE_MENU = """
--- Prize Configuration ---
1. Load preset prize library
2. Add custom prize
3. View prizes (round sequence)
4. Reorder lottery rounds
0. Back"""


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class InputReader:
    """Reads stdin in a background thread so commands can be polled
    while a lottery round is running."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue[str] = queue.Queue()
        self._eof = False
        thread = threading.Thread(target=self._pump, daemon=True)
        thread.start()

    def _pump(self) -> None:
        while True:
            line = self._stream.readline()
            if line == "":
                self._queue.put(EOF_TOKEN)
                return
            self._queue.put(line.strip())

    def read(self, prompt: str = "") -> str:
        """Blocking read of one input line."""
        if prompt:
            print(prompt, end="", flush=True)
        if self._eof:
            return EOF_TOKEN
        item = self._queue.get()
        if item == EOF_TOKEN:
            self._eof = True
        return item

    def poll(self) -> str | None:
        """Non-blocking read. Returns None when no input is pending."""
        if self._eof:
            return EOF_TOKEN
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item == EOF_TOKEN:
            self._eof = True
        return item


class LotterySystemCLI:
    """Interactive command-line controller for the whole system."""

    def __init__(self, input_reader: InputReader | None = None, draw_delay: float = 0.5) -> None:
        self._input = input_reader if input_reader is not None else InputReader()
        self._delay = draw_delay
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._results = ResultManager()
        self._lottery: LotteryManager | None = None
        self._paused = False

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        """Prompt for text. End of input is returned as an empty string."""
        value = self._input.read(prompt)
        if value == EOF_TOKEN:
            return ""
        return value.strip()

    # --------------------------------------------------------------- main loop
    def run(self) -> int:
        print(BANNER)
        while True:
            print(MAIN_MENU)
            choice = self._input.read("Select an option: ")
            if choice == EOF_TOKEN:
                print()
                break
            if choice == "1":
                self._load_participants()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "5":
                self._show_winner_list()
            elif choice == "6":
                self._export()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option, please try again.")
        return 0

    # ------------------------------------------------------- list management
    def _load_participants(self) -> None:
        print("1. Built-in team building list")
        print("2. Upload custom txt list (each line: Name,Department Group)")
        choice = self._ask("Choose list source (1/2): ")
        if choice == "1":
            users, errors = self._list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip('"')
            users, errors = self._list_manager.load_custom_list(path)
        else:
            print("Invalid choice. Participant list unchanged.")
            return

        valid, duplicates = self._list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate Name: '{user.name}' ({user.department}) repeats an earlier entry"
            for user in duplicates
        )
        if problems:
            print(f"Found {len(problems)} problem(s) in the list:")
            for problem in problems:
                print(f"  - {problem}")
            print("Enter 'r' to remove invalid data and keep the valid entries,")
            print("or 't' to terminate the upload.")
            decision = self._ask("Your choice (r/t): ").lower()
            if decision != "r":
                print("Upload terminated. Participant list unchanged.")
                return
            users = valid

        if not users:
            print("No valid participants found. Participant list unchanged.")
            return
        self._users = users
        self._lottery = None
        print(f"Loaded {len(users)} participants.")
        self._show_groups()

    def _show_groups(self) -> None:
        if not self._users:
            print("No participant list loaded.")
            return
        info = self._list_manager.get_group_info(self._users)
        print("\nDepartment groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} member(s)")

    # ------------------------------------------------------ prize management
    def _prize_menu(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._input.read("Select an option: ")
            if choice in (EOF_TOKEN, "0"):
                return
            if choice == "1":
                errors = self._prize_manager.load_default_prizes()
                for error in errors:
                    print(error)
                print("Preset prize library loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            else:
                print("Invalid option, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Prize quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Error: quantity must be an integer.")
            return
        groups = self._choose_groups()
        drawer = self._choose_drawer()
        try:
            self._prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize '{name.strip()}' added.")

    def _choose_groups(self) -> list[str]:
        if self._users:
            groups = list(self._list_manager.get_group_info(self._users).keys())
            print("Department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
            hint = "numbers or names"
        else:
            groups = []
            print("No participant list loaded; enter group names directly.")
            hint = "names"
        raw = self._ask(f"Avoidance groups, comma-separated {hint} (empty for none): ")
        result: list[str] = []
        for token in (part.strip() for part in raw.split(",")):
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                result.append(groups[int(token) - 1])
            else:
                result.append(token)
        return result

    def _choose_drawer(self) -> str | None:
        print("Associated lottery person:")
        print("  0. None")
        for index, person in enumerate(DRAWER_OPTIONS, start=1):
            print(f"  {index}. {person}")
        while True:
            raw = self._ask("Select (0-4): ")
            if raw in ("", "0"):
                return None
            if raw.isdigit() and 1 <= int(raw) <= len(DRAWER_OPTIONS):
                return DRAWER_OPTIONS[int(raw) - 1]
            print("Invalid selection, please try again.")

    def _show_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery round sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {groups} | Associated person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        raw = self._ask("Enter new order as serial numbers (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            print("Round sequence updated.")
            self._show_prizes()
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ------------------------------------------------------- lottery process
    def _start_lottery(self) -> None:
        if not self._users:
            print("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please set up prizes first.")
            return

        self._results = ResultManager()
        self._lottery = LotteryManager(self._users)
        print("\n##### Lottery started #####")
        print("Control commands: 'pause', 'continue', 'terminate'")
        for index, prize in enumerate(prizes, start=1):
            if not self._run_round(prize, index, len(prizes)):
                print("Lottery process exited.")
                break
        else:
            print("\n##### All lottery rounds completed #####")
        self._show_winner_list()

    def _run_round(self, prize: Prize, index: int, total: int) -> bool:
        """Run one round. Returns False if the whole lottery must stop."""
        assert self._lottery is not None
        self._paused = False
        print(f"\n--- Round {index}/{total}: {prize.name} ---")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._lottery.describe_rules(prize)}")

        round_winners: list[User] = []
        for position in range(1, prize.quantity + 1):
            status = self._apply_control()
            if status == "exit":
                self._print_round_summary(index, round_winners)
                return False
            if status == "terminate":
                print("Current round terminated by operator.")
                break
            if self._lottery.eligible_count(prize) == 0:
                print("No eligible participants remain for this prize. Round ends.")
                break

            print(f"Currently drawing the {_ordinal(position)} winner...", flush=True)
            time.sleep(self._delay)
            user = self._lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            self._results.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self._print_round_summary(index, round_winners)
        return True

    def _print_round_summary(self, index: int, winners: list[User]) -> None:
        print(f"Round {index} results ({len(winners)} winner(s)):")
        for position, user in enumerate(winners, start=1):
            print(f"  {position}. {user.name} ({user.department})")

    def _apply_control(self) -> str:
        """Process pending control commands.

        Returns "run" to keep drawing, "terminate" to skip the current round,
        or "exit" when the input stream has ended.
        """
        while True:
            if self._paused:
                command = self._input.read("[PAUSED] Enter 'continue' or 'terminate': ")
            else:
                pending = self._input.poll()
                if pending is None:
                    return "run"
                command = pending
            command = command.strip().lower()
            if command == EOF_TOKEN:
                return "exit"
            if command == "pause":
                if not self._paused:
                    self._paused = True
                    print("Lottery paused. Enter 'continue' to resume or 'terminate' to skip this round.")
            elif command == "continue":
                if self._paused:
                    self._paused = False
                    print("Lottery resumed.")
            elif command == "terminate":
                self._paused = False
                return "terminate"
            elif command:
                print(f"Unknown command '{command}'. Use 'pause', 'continue' or 'terminate'.")

    # ---------------------------------------------------------------- results
    def _show_winner_list(self) -> None:
        prizes = sort_prizes_by_level(self._prize_manager.get_prizes())
        grouped = self._results.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            print("No winners yet.")
            return
        print("\n========== Winner List ==========")
        for prize in prizes:
            winners = grouped.get(prize.name, [])
            if not winners:
                continue
            print(f"\n{prize.name}:")
            for position, winner in enumerate(winners, start=1):
                print(
                    f"  {position}. {winner.user.name} | {winner.user.department} | "
                    f"{prize.name} | {winner.winning_time}"
                )

    def _export(self) -> None:
        if not self._results.winners:
            print("No winners to export yet. Run the lottery first.")
            return
        success, message = self._results.export_to_csv(self._prize_manager.get_prizes())
        print(message)
        if not success:
            print("Please check the file permissions and try again.")


def main() -> int:
    """Application entry point."""
    cli = LotterySystemCLI()
    try:
        return cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
