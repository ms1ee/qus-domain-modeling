"""Command-line interface and lottery process control."""
from __future__ import annotations

import queue
import re
import sys
import threading
import time
from typing import TextIO

from lottery_system.models import Prize, User, normalize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import (
    DRAWER_OPTIONS,
    LotteryManager,
    describe_prize_rule,
)
from lottery_system.services.prize_manager import PrizeManager

DRAW_INTERVAL_SECONDS = 0.5
CONTROL_POLL_SECONDS = 0.05


class InputReader:
    """Reads stdin in a background thread so control commands can be received during a lottery."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        while True:
            try:
                line = self._stream.readline()
            except (OSError, ValueError):
                line = ""
            if line == "":
                self._queue.put(None)
                return
            self._queue.put(line.strip())

    def read(self) -> str:
        """Blocking read of the next input line. Raises EOFError when input is closed."""
        item = self._queue.get()
        if item is None:
            self._queue.put(None)
            raise EOFError
        return item

    def poll(self) -> str | None:
        """Non-blocking read. Returns None when no input is pending."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item is None:
            self._queue.put(None)
            return None
        return item


def ordinal(number: int) -> str:
    """Format an integer as an English ordinal, e.g. 1st, 2nd, 11th."""
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def parse_numbers(text: str) -> list[int] | None:
    """Parse whitespace/comma separated integers. Returns None if any token is not an integer."""
    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


class LotterySystemCLI:
    """Interactive command-line application."""

    def __init__(self, reader: InputReader | None = None, draw_interval: float = DRAW_INTERVAL_SECONDS) -> None:
        self.reader = reader or InputReader()
        self.draw_interval = draw_interval
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_completed = False

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        return self.reader.read()

    def _ask_int(self, prompt: str, minimum: int, maximum: int | None = None) -> int:
        while True:
            text = self._ask(prompt).strip()
            try:
                value = int(text)
            except ValueError:
                print("Please enter an integer.")
                continue
            if value < minimum or (maximum is not None and value > maximum):
                if maximum is None:
                    print(f"Please enter a value of at least {minimum}.")
                else:
                    print(f"Please enter a value between {minimum} and {maximum}.")
                continue
            return value

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        handlers = {
            "1": self._load_default_list,
            "2": self._upload_custom_list,
            "3": self._show_groups,
            "4": self._prize_menu,
            "5": self._start_lottery,
            "6": self._show_results,
            "7": self._export_results,
        }
        print("Welcome to the Team Building Smart Lottery System.")
        try:
            while True:
                self._print_main_menu()
                choice = self._ask("Select an option: ").strip()
                if choice == "0":
                    break
                handler = handlers.get(choice)
                if handler is None:
                    print("Invalid option. Please try again.")
                    continue
                handler()
        except EOFError:
            print("\nInput closed.")
        print("Goodbye.")

    def _print_main_menu(self) -> None:
        print("\n========== Main Menu ==========")
        print(f"Participants loaded: {len(self.users)} | Prizes configured: {len(self.prize_manager.get_prizes())}")
        print("1. Load built-in default participant list")
        print("2. Upload custom participant list (txt)")
        print("3. View department groups and headcount")
        print("4. Prize configuration")
        print("5. Start lottery")
        print("6. View winner results")
        print("7. Export winner results")
        print("0. Exit")

    # ------------------------------------------------------------- list module
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def _upload_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file (format: Name,Department per line): ").strip().strip('"')
        if not path:
            print("Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        if any(error.startswith("File Error") for error in errors):
            for error in errors:
                print(error)
            return
        if not users and not errors:
            print("The file contains no participant entries. Upload cancelled.")
            return
        self._accept_list(users, errors)

    def _accept_list(self, users: list[User], errors: list[str]) -> None:
        """Verify a loaded list, prompt for cleanup options when problems are found, then apply it."""
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self._set_users(valid)
            return

        print("\nIssues detected in the participant list:")
        for error in errors:
            print(f"  - {error}")
        for duplicate in duplicates:
            print(f"  - Duplicate name: {duplicate.name} ({duplicate.department})")
        print(f"Valid entries available: {len(valid)}")
        print("Options:")
        print("  [1] Remove invalid and duplicate entries and keep the rest")
        print("  [2] Terminate upload")
        print("  [3] Manually remove specific names from the valid list")
        choice = self._ask("Select an option: ").strip()
        if choice == "1":
            self._set_users(valid)
        elif choice == "3":
            raw = self._ask("Enter names to remove (comma separated): ")
            remove = {normalize(name) for name in raw.split(",") if name.strip()}
            kept = [user for user in valid if normalize(user.name) not in remove]
            self._set_users(kept)
        else:
            print("Upload terminated. The current participant list is unchanged.")

    def _set_users(self, users: list[User]) -> None:
        if not users:
            print("No valid participants remain. The current participant list is unchanged.")
            return
        self.users = list(users)
        self.lottery = None
        self.lottery_completed = False
        print(f"Participant list updated: {len(self.users)} participants loaded.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid department groups:")
        for department, count in info.items():
            print(f"  - {department}: {count} people")
        print(f"Total groups: {len(info)} | Total participants: {len(self.users)}")

    # ------------------------------------------------------------- prize module
    def _prize_menu(self) -> None:
        handlers = {
            "1": self._load_default_prizes,
            "2": self._add_custom_prize,
            "3": self._view_prizes,
            "4": self._reorder_prizes,
        }
        locked_options = {"1", "2", "4"}
        while True:
            print("\n----- Prize Configuration -----")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes and rules")
            print("4. Adjust lottery sequence")
            print("0. Back to main menu")
            choice = self._ask("Select an option: ").strip()
            if choice == "0":
                return
            handler = handlers.get(choice)
            if handler is None:
                print("Invalid option. Please try again.")
                continue
            if choice in locked_options and self.lottery_completed:
                print("The lottery has already been completed. Load a new participant list to reconfigure.")
                continue
            handler()

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        print("Preset prize library loaded.")
        for error in errors:
            print(f"  - {error}")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity = self._ask_int("Quantity (positive integer): ", 1)

        print("Associated lottery person:")
        print("  0. None")
        for index, drawer in enumerate(DRAWER_OPTIONS, start=1):
            print(f"  {index}. {drawer}")
        selection = self._ask_int("Select lottery person: ", 0, len(DRAWER_OPTIONS))
        drawer = None if selection == 0 else DRAWER_OPTIONS[selection - 1]

        avoid_groups = self._select_avoid_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Could not add prize: {exc}")
            return
        print(f"Prize added at position {len(self.prize_manager.get_prizes())}: {prize.name}")

    def _select_avoid_groups(self) -> list[str]:
        if not self.users:
            print("No participant list loaded; avoidance groups cannot be selected.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        print("Available groups (select to avoid):")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        prompt = "Select avoidance groups (comma-separated numbers, blank for none): "
        while True:
            numbers = parse_numbers(self._ask(prompt))
            if numbers is not None and all(1 <= number <= len(groups) for number in numbers):
                break
            prompt = f"Invalid selection. Enter numbers between 1 and {len(groups)}, or leave blank: "
        return [groups[number - 1] for number in dict.fromkeys(numbers)]

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            print(f"{index}. {prize.name} | Quantity: {prize.quantity} | Drawer: {prize.associated_drawer or 'None'}")
            print(f"   Rule: {describe_prize_rule(prize)}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to adjust the sequence.")
            return
        self._print_sequence(prizes)
        numbers = parse_numbers(
            self._ask("Enter the new order as serial numbers (e.g. '2 1 3'): ")
        )
        if numbers is None or not self.prize_manager.reorder_prizes(numbers):
            print(f"Invalid order. Each serial number from 1 to {len(prizes)} must appear exactly once.")
            return
        print("Lottery sequence updated.")
        self._print_sequence(self.prize_manager.get_prizes())

    @staticmethod
    def _print_sequence(prizes: list[Prize]) -> None:
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} (quantity: {prize.quantity})")

    # ---------------------------------------------------------- lottery module
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery_completed:
            print("The lottery is already completed for the current list. Load a list to start a new lottery.")
            return
        total_quantity = sum(prize.quantity for prize in prizes)
        if total_quantity > len(self.users):
            print(
                f"Warning: total prize quantity ({total_quantity}) exceeds participants "
                f"({len(self.users)}); some rounds may draw fewer winners."
            )
        answer = self._ask("Start the lottery now? (y/n): ").strip().lower()
        if answer not in ("y", "yes"):
            print("Lottery cancelled.")
            return

        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        print("\nLottery started. Commands: 'pause' to interrupt, 'continue' to resume, 'terminate' to end the current round.")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)
        self.lottery_completed = True
        print("\nAll lottery rounds completed.")
        self._show_results()

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Drawer: {prize.associated_drawer or 'None'}")
        print(f"Rule: {self.lottery.describe_rules(prize)}")

        winners: list[User] = []
        terminated = False
        for position in range(1, prize.quantity + 1):
            if self._pump_controls(self.draw_interval):
                terminated = True
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            winner = self.lottery.draw_one(prize)
            if winner is None:
                print("No eligible candidates remain for this prize. The round ends early.")
                break
            winners.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")

        self.lottery.finish_round(prize, winners)
        status = "terminated by operator" if terminated else "completed"
        print(f"Round {index} {status}: {len(winners)}/{prize.quantity} winner(s) drawn.")

    def _pump_controls(self, duration: float) -> bool:
        """Wait for `duration` seconds while handling control commands.

        Returns True if the current round should be terminated.
        """
        deadline = time.monotonic() + duration
        while True:
            command = self.reader.poll()
            if command is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                time.sleep(min(CONTROL_POLL_SECONDS, remaining))
                continue

            command = command.strip().lower()
            if not command:
                continue
            if command == "pause":
                print("[PAUSED] Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    answer = self.reader.read().strip().lower()
                    if answer == "continue":
                        print("[RESUMED] Lottery resumed.")
                        break
                    if answer == "terminate":
                        print("[TERMINATED] Current round terminated. Remaining draws are skipped.")
                        return True
                    print("Lottery is paused. Type 'continue' or 'terminate'.")
            elif command == "terminate":
                print("[TERMINATED] Current round terminated. Remaining draws are skipped.")
                return True
            elif command == "continue":
                print("Lottery is not paused.")
            else:
                print(f"Unknown command '{command}'. Use 'pause' or 'terminate' during the lottery.")

    # ---------------------------------------------------------- results module
    def _show_results(self) -> None:
        if self.lottery is None:
            print("No lottery has been run yet.")
            return
        prizes = self.prize_manager.get_prizes()
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        total = sum(len(winners) for winners in grouped.values())
        if total == 0:
            print("No winners recorded yet.")
            return
        print("\n=== Winner List ===")
        print(f"{'Name':<20} | {'Department':<28} | Prize")
        for prize_name, winners in grouped.items():
            for winner in winners:
                print(f"{winner.user.name:<20} | {winner.user.department:<28} | {prize_name}")

    def _export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export.")
            return
        _, message = self.lottery.result_manager.export_to_csv(self.prize_manager.get_prizes())[0:1] + (
            self.lottery.result_manager.export_to_csv(self.prize_manager.get_prizes())[1],
        )
        print(message)


def main() -> None:
    """Application entry point."""
    app = LotterySystemCLI()
    app.run()


if __name__ == "__main__":
    main()
