"""Interactive command-line interface for the lottery system."""

from __future__ import annotations

import queue
import sys
import threading
import time

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


MAIN_MENU = """
==== Team Building Smart Lottery System ====
1. Load default team building list
2. Load custom list (txt file)
3. View department groups
4. Prize configuration
5. Start lottery
6. Show winner list
7. Export results (txt/CSV)
0. Exit
"""

PRIZE_MENU = """
---- Prize Configuration ----
1. Load default prize library
2. Add custom prize
3. Set avoidance groups for a prize
4. Reorder prizes (lottery sequence)
5. Show prizes
0. Back to main menu
"""

LOTTERY_CONTROLS = "Lottery controls: 'pause' to interrupt, 'continue' to resume, 'terminate' to end this round."


class InputReader:
    """Reads stdin in a background thread so lottery commands can be polled."""

    def __init__(self, stream=None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._pump, name="stdin-reader", daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.strip())
        except (OSError, ValueError):
            pass
        self._queue.put(None)

    def _unwrap(self, item):
        if item is None:
            self._queue.put(None)  # keep the EOF marker available for later reads
            raise EOFError("Input stream closed.")
        return item

    def get(self) -> str:
        """Blocking read of one input line."""
        return self._unwrap(self._queue.get())

    def poll(self):
        """Non-blocking read; returns None when no input is pending."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        return self._unwrap(item)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    """Drives the list management, prize configuration, lottery and result workflows."""

    def __init__(self, reader: InputReader | None = None, draw_delay: float = 0.5) -> None:
        self.reader = reader if reader is not None else InputReader()
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_completed = False

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        return self.reader.get().strip()

    def _ask_int(self, prompt: str) -> int | None:
        raw = self._ask(prompt)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            return None

    def _set_users(self, users: list[User]) -> None:
        self.users = list(users)
        self.lottery = None
        self.lottery_completed = False
        print(f"List loaded successfully: {len(self.users)} valid participant(s).")

    def _accept_users(self, users: list[User], errors: list[str]) -> None:
        valid, duplicates = self.list_manager.validate_users(users)

        if errors:
            print("Format errors detected:")
            for err in errors:
                print(f"  {err}")
        if duplicates:
            print("Duplicate names detected (later entries will be removed):")
            for dup in duplicates:
                print(f"  {dup.name} ({dup.department})")

        if not errors and not duplicates:
            self._set_users(valid)
            return

        choice = self._ask(
            "Enter 'remove' to discard invalid/duplicate data and continue, "
            "or 'terminate' to cancel the upload: "
        ).lower()
        if choice == "remove":
            if valid:
                self._set_users(valid)
            else:
                print("No valid participants remain. Upload cancelled.")
        else:
            print("Upload terminated. Current list is unchanged.")

    def _print_prizes(self, prizes: list[Prize]) -> None:
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            groups = ", ".join(prize.avoid_groups) or "-"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {groups}"
            )

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        try:
            while True:
                print(MAIN_MENU)
                choice = self._ask("Select an option: ")
                if choice == "0":
                    break
                if choice == "1":
                    users, errors = self.list_manager.load_default_list()
                    self._accept_users(users, errors)
                elif choice == "2":
                    path = self._ask("Path to custom txt list: ").strip('"').strip()
                    users, errors = self.list_manager.load_custom_list(path)
                    self._accept_users(users, errors)
                elif choice == "3":
                    self.show_groups()
                elif choice == "4":
                    self.prize_menu()
                elif choice == "5":
                    self.start_lottery()
                elif choice == "6":
                    self.show_summary()
                elif choice == "7":
                    self.export_results()
                else:
                    print("Invalid option, please try again.")
        except EOFError:
            print("\nInput closed.")
        print("Goodbye!")

    # ------------------------------------------------------------ list actions
    def show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} person(s)")

    # ----------------------------------------------------------- prize actions
    def prize_menu(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "0":
                return
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    print("Some default prizes could not be added:")
                    for err in errors:
                        print(f"  {err}")
                else:
                    print("Default prize library loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                prizes = self.prize_manager.get_prizes()
                if not prizes:
                    print("No prizes configured.")
                else:
                    self._print_prizes(prizes)
            else:
                print("Invalid option, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_int("Quantity: ")
        if quantity is None or quantity < 1:
            print("Error: quantity must be a positive integer.")
            return
        groups_raw = self._ask("Avoidance groups (comma-separated, empty for none): ")
        drawer = self._ask("Associated lottery person (empty for none): ")
        groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer or None)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print("Prize added successfully.")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes(prizes)
        index = self._ask_int("Prize serial number: ")
        if index is None or not 1 <= index <= len(prizes):
            print("Invalid prize serial number.")
            return
        if self.users:
            print("Available groups: " + ", ".join(self.list_manager.get_group_info(self.users).keys()))
        raw = self._ask("Avoidance groups (comma-separated, empty to clear): ")
        groups = [g.strip() for g in raw.split(",") if g.strip()]
        if self.users:
            known = {d.casefold() for d in self.list_manager.get_group_info(self.users)}
            unknown = [g for g in groups if g.casefold() not in known]
            if unknown:
                print(f"Warning: group(s) not in current list: {', '.join(unknown)}")
        self.prize_manager.set_avoid_groups(index, groups)
        print("Avoidance groups updated.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are required to reorder.")
            return
        self._print_prizes(prizes)
        raw = self._ask("Enter new order as serial numbers (e.g. 3 1 2): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated:")
            self._print_prizes(self.prize_manager.get_prizes())
        else:
            print(f"Invalid order: must contain each serial number 1-{len(prizes)} exactly once.")

    # ---------------------------------------------------------- lottery actions
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self.lottery_completed:
            print("This lottery session is already completed. Reload a list to start a new session.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)

        print("\nLottery starts!")
        print(LOTTERY_CONTROLS)
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
        self.lottery_completed = True
        print("\nAll lottery rounds completed.")
        self.show_summary()

    def _handle_controls(self) -> bool:
        """Process pending control commands. Returns True if the current round must be terminated."""
        command = self.reader.poll()
        if not command:
            return False
        command = command.lower()
        if command == "pause":
            print("[PAUSED] Enter 'continue' to resume or 'terminate' to end this round.")
            while True:
                answer = self.reader.get().lower()
                if answer == "continue":
                    print("[RESUMED] Lottery continues.")
                    return False
                if answer == "terminate":
                    return True
                print("Lottery is paused. Only 'continue' or 'terminate' are accepted.")
        if command == "terminate":
            return True
        if command == "continue":
            print("Lottery is not paused.")
            return False
        print(f"Unknown command '{command}' ignored. {LOTTERY_CONTROLS}")
        return False

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {index}/{total} ===")
        print(f"Prize: {prize.name} | Quantity: {prize.quantity}")
        print(f"Rule: {LotteryManager.describe_rule(prize)}")

        winners: list[User] = []
        terminated = False
        for position in range(1, prize.quantity + 1):
            if self._handle_controls():
                terminated = True
                break
            print(f"Currently drawing the {_ordinal(position)} winner...")
            time.sleep(self.draw_delay)
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.lottery.finish_round(prize, winners)
        if terminated:
            print("Round terminated manually; remaining prizes of this round are skipped.")
        if winners:
            print(f"Round results for {prize.name} (winning order):")
            for order, user in enumerate(winners, start=1):
                print(f"  {order}. {user.name} ({user.department})")
        else:
            print("No winners in this round.")

    def show_summary(self) -> None:
        if self.lottery is None:
            print("No lottery results yet.")
            return
        by_prize = self.lottery.results.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n==== Winner List (by prize level) ====")
        if not by_prize:
            print("No prizes configured.")
            return
        for prize_name, winners in by_prize.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.prize_order}. {winner.user.name} ({winner.user.department}) "
                    f"- {winner.winning_time}"
                )

    def export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export yet.")
            return
        _, message = self.lottery.results.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    cli = LotterySystemCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
