"""Command-line interface for the team building lottery system."""

from __future__ import annotations

import queue
import sys
import threading
import time
from typing import Optional, TextIO

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class InputReader:
    """Reads stdin in a background thread so commands can be polled during a lottery."""

    def __init__(self, stream: Optional[TextIO] = None) -> None:
        self._stream = stream or sys.stdin
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                line = self._stream.readline()
            except (OSError, ValueError):
                line = ""
            if line == "":
                self._queue.put(None)
                return
            self._queue.put(line.rstrip("\r\n"))

    def readline(self) -> str:
        """Blocking read of the next line. Raises EOFError at end of input."""
        item = self._queue.get()
        if item is None:
            self._queue.put(None)
            raise EOFError
        return item

    def poll(self) -> Optional[str]:
        """Non-blocking read. Returns None if no line is available."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item is None:
            self._queue.put(None)
            raise EOFError
        return item


def ordinal(number: int) -> str:
    """Format an integer as an English ordinal, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive menu-driven controller."""

    def __init__(self, reader: Optional[InputReader] = None) -> None:
        self.reader = reader or InputReader()
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.result_manager = ResultManager()
        self.lottery_done = False
        self._menu = {
            "1": self.load_list_menu,
            "2": self.show_groups,
            "3": self.prize_menu,
            "4": self.start_lottery,
            "5": self.show_results,
            "6": self.export_results,
        }

    # ------------------------------------------------------------------ io
    def ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        return self.reader.readline().strip()

    def _ask_positive_int(self, prompt: str) -> Optional[int]:
        while True:
            raw = self.ask(prompt)
            if raw == "":
                return None
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a whole number.")
                continue
            if value <= 0:
                print("Value must be greater than zero.")
                continue
            return value

    # ---------------------------------------------------------------- main
    def run(self) -> int:
        print("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                self._print_main_menu()
                choice = self.ask("Select an option: ")
                if choice == "0":
                    print("Goodbye!")
                    return 0
                handler = self._menu.get(choice)
                if handler is None:
                    print("Invalid option. Please try again.")
                    continue
                handler()
        except EOFError:
            print("\nInput closed. Exiting.")
            return 0

    def _print_main_menu(self) -> None:
        print("\n==== Main Menu ====")
        print("1. Load participant list")
        print("2. View department groups")
        print("3. Prize configuration")
        print("4. Start lottery")
        print("5. Show winner list")
        print("6. Export winner list")
        print("0. Exit")

    # ---------------------------------------------------------- list menu
    def load_list_menu(self) -> None:
        print("\n-- Load Participant List --")
        print("1. Built-in team building list")
        print("2. Custom txt list (each line: Name,Department Group)")
        print("0. Back")
        choice = self.ask("Select: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            self._process_loaded(users, errors)
        elif choice == "2":
            path = self.ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
            self._process_loaded(users, errors)

    def _process_loaded(self, users: list[User], errors: list[str]) -> None:
        if errors:
            print(f"Found {len(errors)} format/file error(s):")
            for message in errors:
                print(f"  - {message}")
        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
        if (errors or duplicates) and users:
            print("Choose how to proceed:")
            print("  r - remove invalid/duplicate entries and continue")
            print("  t - terminate upload")
            if self.ask("Your choice (r/t): ").lower() != "r":
                print("Upload terminated. Participant list was not changed.")
                return
        if not valid:
            print("No valid participants found. Participant list was not loaded.")
            return
        self.users = valid
        print(f"Participant list loaded: {len(valid)} valid participant(s).")
        self.show_groups()

    def show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\n-- Department Groups --")
        for department, count in info.items():
            print(f"  {department}: {count} people")

    # --------------------------------------------------------- prize menu
    def prize_menu(self) -> None:
        while True:
            print("\n-- Prize Configuration --")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes")
            print("4. Adjust lottery order")
            print("0. Back")
            choice = self.ask("Select: ")
            if choice == "0":
                return
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for message in errors:
                    print(f"  - {message}")
                print("Preset prizes loaded.")
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.view_prizes()
            elif choice == "4":
                self.reorder_prizes()
            else:
                print("Invalid option.")

    def add_custom_prize(self) -> None:
        name = self.ask("Prize name: ")
        quantity = self._ask_positive_int("Quantity: ")
        if quantity is None:
            print("Prize not added.")
            return
        if self.users:
            print("Available groups: " + ", ".join(self.list_manager.get_group_info(self.users).keys()))
        groups_raw = self.ask("Avoidance groups (comma-separated, blank for none): ")
        avoid = [g.strip() for g in groups_raw.split(",") if g.strip()]
        drawer = self.ask("Associated lottery person (blank for none): ")
        try:
            self.prize_manager.add_prize(name, quantity, avoid, drawer or None)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print("Prize added.")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nCurrent lottery order:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {index}. {prize.name} | quantity: {prize.quantity} | drawer: {drawer} | avoid: {avoid}")

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to adjust the order.")
            return
        self.view_prizes()
        raw = self.ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery order updated.")
        else:
            print("Invalid order: every prize serial number must appear exactly once.")

    # ------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self.lottery_done:
            answer = self.ask("A lottery was already run. Clear previous results and restart? (y/n): ")
            if answer.lower() != "y":
                return
            self.result_manager = ResultManager()

        lottery = LotteryManager(self.users)
        total = len(prizes)
        print("\n=== Lottery started ===")
        print("Commands during the lottery: pause | continue | terminate")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(lottery, prize, round_no, total)
        self.lottery_done = True
        print("\n=== All lottery rounds completed ===")
        self.show_results()

    def _apply_command(self, raw: str, state: dict) -> None:
        command = raw.strip().lower()
        if not command:
            return
        if command == "pause":
            if not state["paused"]:
                state["paused"] = True
                print("[Lottery paused] Type 'continue' to resume or 'terminate' to end this round.")
        elif command == "continue":
            if state["paused"]:
                state["paused"] = False
                print("[Lottery resumed]")
        elif command == "terminate":
            state["terminated"] = True
            state["paused"] = False
            print("[Round terminated] Skipping to the next round.")
        else:
            print(f"Unknown command '{command}'. Available: pause, continue, terminate.")

    def _pace(self, state: dict, seconds: float = 0.5) -> None:
        """Wait for the given time while processing any commands typed by the user."""
        deadline = time.monotonic() + seconds
        while not state["terminated"]:
            command = self.reader.poll()
            if command is not None:
                self._apply_command(command, state)
                continue
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)

    def _run_round(self, lottery: LotteryManager, prize: Prize, round_no: int, total: int) -> list[User]:
        print(f"\n--- Round {round_no}/{total}: {prize.name} ---")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        state = {"paused": False, "terminated": False}
        drawn: list[User] = []
        while len(drawn) < prize.quantity:
            print(f"Currently drawing the {ordinal(len(drawn) + 1)} winner...")
            self._pace(state)
            while state["paused"] and not state["terminated"]:
                self._apply_command(self.reader.readline(), state)
            if state["terminated"]:
                break
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize; the round ends.")
                break
            drawn.append(user)
            self.result_manager.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        lottery.complete_round(prize, drawn)
        print(f"--- Round {round_no} results ({len(drawn)}/{prize.quantity}) ---")
        if not drawn:
            print("  (no winners in this round)")
        for index, user in enumerate(drawn, start=1):
            print(f"  {index}. {user.name} ({user.department})")
        return drawn

    # ------------------------------------------------------------ results
    def show_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n=== Complete Winner List ===")
        for prize in prizes:
            winners = grouped.get(prize.name, [])
            print(f"{prize.name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.user.name} ({winner.user.department}) - {prize.name}")

    def export_results(self) -> None:
        if not self.result_manager.get_all_winners():
            print("No lottery results to export.")
            return
        ok, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> int:
    cli = LotterySystemCLI()
    try:
        return cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
