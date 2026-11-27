"""Command-line interface: list setup, prize configuration and lottery control."""

import queue
import sys
import threading
import time

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LI_BIN, LotteryManager
from lottery_system.services.prize_manager import PrizeManager

DEFAULT_DRAW_DELAY = 0.5
_EOF = object()


class InputClosed(Exception):
    """Raised when standard input has been closed."""


class CommandReader:
    """Reads stdin in a background thread so commands can be polled during a draw."""

    def __init__(self, stream=None):
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        thread = threading.Thread(target=self._pump, daemon=True)
        thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(_EOF)

    def read(self) -> str:
        """Blocking read of one line. Raises InputClosed at end of input."""
        item = self._queue.get()
        if item is _EOF:
            self._queue.put(_EOF)
            raise InputClosed()
        return item

    def poll(self) -> str | None:
        """Non-blocking read. Returns None if no line is waiting."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item is _EOF:
            self._queue.put(_EOF)
            return None
        return item


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _parse_numbers(text: str) -> list[int] | None:
    """Parse whitespace/comma separated integers. Returns None if any token is invalid."""
    tokens = text.replace(",", " ").split()
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


class LotterySystemCLI:
    """Interactive menu-driven controller for the lottery system."""

    def __init__(self, reader: CommandReader | None = None, draw_delay: float = DEFAULT_DRAW_DELAY):
        self.reader = reader if reader is not None else CommandReader()
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self._actions = {
            "1": self.load_default_list,
            "2": self.upload_custom_list,
            "3": self.view_groups,
            "4": self.load_default_prizes,
            "5": self.add_custom_prize,
            "6": self.manage_prize_order,
            "7": self.start_lottery,
            "8": self.export_results,
        }

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        return self.reader.read().strip()

    def _show_menu(self) -> None:
        print()
        print("=" * 56)
        print("   Team Building Smart Lottery System")
        print("=" * 56)
        print("  1. Load built-in default team building list")
        print("  2. Upload custom txt list (Name,Department per line)")
        print("  3. View department groups and headcounts")
        print("  4. Load default prize library")
        print("  5. Add custom prize")
        print("  6. View prizes / adjust lottery sequence")
        print("  7. Start lottery")
        print("  8. Export winner list (txt, CSV format)")
        print("  0. Exit")
        print("-" * 56)

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    def _print_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department}: {count} people")

    def _print_prizes(self, prizes) -> None:
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            avoid = ", ".join(prize.avoid_groups) or "-"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} "
                f"| lottery person: {drawer} | avoid groups: {avoid}"
            )

    # ------------------------------------------------------------ main loop
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            self._show_menu()
            choice = self._ask("Select an option: ")
            if choice == "0":
                print("Goodbye!")
                return
            action = self._actions.get(choice)
            if action is None:
                print("Invalid option, please try again.")
                continue
            action()

    # -------------------------------------------------------- list management
    def _accept_list(self, users: list[User], errors: list[str]) -> bool:
        if errors:
            print(f"Found {len(errors)} problematic line(s):")
            for error in errors:
                print(f"  - {error}")
            choice = self._ask(
                "Enter 'r' to remove invalid data and continue, or 't' to terminate the upload: "
            ).lower()
            if choice != "r":
                print("Upload terminated.")
                return False
            print("Invalid data removed.")

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
            choice = self._ask(
                "Enter 'r' to remove duplicates and continue, or 't' to terminate the upload: "
            ).lower()
            if choice != "r":
                print("Upload terminated.")
                return False
            users = valid

        if not users:
            print("No valid participants found. The list was not loaded.")
            return False

        self.users = users
        print(f"Loaded {len(users)} participant(s).")
        self._print_groups()
        return True

    def load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def upload_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file: ").strip('"').strip("'")
        users, errors = self.list_manager.load_custom_list(path)
        self._accept_list(users, errors)

    def view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded yet.")
            return
        self._print_groups()

    # ---------------------------------------------------------- prize config
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            print("Some default prizes could not be loaded:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Default prize library loaded.")

    def add_custom_prize(self) -> None:
        name = self._ask("Prize name (blank to cancel): ")
        if not name:
            print("Cancelled.")
            return

        quantity_text = self._ask("Prize quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            print("Quantity must be a positive integer. Prize not added.")
            return

        drawer = self._ask("Associated lottery person (blank for none): ") or None

        avoid_groups: list[str] = []
        groups = self._group_names()
        if groups:
            print("Department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
            text = self._ask("Avoidance group numbers, comma separated (blank for none): ")
            if text:
                indexes = _parse_numbers(text)
                if indexes is None or any(not 1 <= index <= len(groups) for index in indexes):
                    print("Invalid group selection. Prize not added.")
                    return
                avoid_groups = [groups[index - 1] for index in dict.fromkeys(indexes)]

        if drawer == LI_BIN and avoid_groups:
            print("Note: the Li Bin rule ignores avoidance groups.")

        try:
            prize = self.prize_manager.add_prize(name, int(quantity_text), avoid_groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity: {prize.quantity})")

    def manage_prize_order(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        print("Current lottery sequence:")
        self._print_prizes(prizes)
        text = self._ask("Enter new order as serial numbers, e.g. '3 1 2' (blank to keep): ")
        if not text:
            return
        order = _parse_numbers(text)
        if not order or not self.prize_manager.reorder_prizes(order):
            print("Invalid order. Each prize number must appear exactly once.")
            return
        print("Lottery sequence updated:")
        self._print_prizes(self.prize_manager.get_prizes())

    # --------------------------------------------------------- lottery control
    def _check_controls(self) -> bool:
        """Process queued control commands. Returns False if the current round should stop."""
        command = self.reader.poll()
        while command is not None:
            command = command.strip().lower()
            if command == "pause":
                print("[PAUSED] Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    answer = self.reader.read().strip().lower()
                    if answer == "continue":
                        print("[RESUMED]")
                        break
                    if answer == "terminate":
                        print("[TERMINATED] Current round ended early.")
                        return False
                    print("Lottery is paused. Type 'continue' or 'terminate'.")
            elif command == "terminate":
                print("[TERMINATED] Current round ended early.")
                return False
            elif command == "continue":
                print("Lottery is already running.")
            elif command:
                print(f"Unknown command '{command}'. Available: pause, continue, terminate.")
            command = self.reader.poll()
        return True

    def _run_round(self, index: int, total: int, prize) -> None:
        assert self.lottery is not None
        print()
        print(f"=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self.lottery.describe_rule(prize)}")

        round_winners: list[User] = []
        if not self.lottery.has_candidates(prize):
            print("No eligible candidates for this prize; round skipped.")
        else:
            for position in range(1, prize.quantity + 1):
                if not self._check_controls():
                    break
                if not self.lottery.has_candidates(prize):
                    print("No eligible candidates remain; round ends early.")
                    break
                print(f"Currently drawing the {_ordinal(position)} winner...", flush=True)
                time.sleep(self.draw_delay)
                if not self._check_controls():
                    break
                winner = self.lottery.draw_one(prize)
                if winner is None:
                    print("No eligible candidates remain; round ends early.")
                    break
                round_winners.append(winner)
                print(
                    f"Congratulations {winner.name} ({winner.department}) "
                    f"for winning {prize.name}!"
                )

        self.lottery.record_round_result(prize, round_winners)

        print(f"--- Round results: {prize.name} ---")
        if not round_winners:
            print("  No winners in this round.")
        for number, winner in enumerate(round_winners, start=1):
            print(f"  {number}. {winner.name} ({winner.department})")

    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is not None:
            print("A lottery has already been run in this session. Restart the program to run again.")
            return

        self.lottery = LotteryManager(self.users)
        print()
        print("Lottery starts! During a draw you may type: pause / continue / terminate")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)

        self._show_final_results(prizes)

    def _show_final_results(self, prizes) -> None:
        assert self.lottery is not None
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        print()
        print("=" * 56)
        print("   Final Winner List")
        print("=" * 56)
        for prize in prizes:
            print(f"{prize.name}:")
            winners = grouped[prize.name]
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  - {winner.user.name} ({winner.user.department})")

        answer = self._ask("Export the winner list now? (y/n): ").lower()
        if answer == "y":
            self._export(prizes)

    # ------------------------------------------------------------- results
    def _export(self, prizes) -> None:
        assert self.lottery is not None
        _, message = self.lottery.result_manager.export_to_csv(prizes)
        print(message)

    def export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export yet.")
            return
        self._export(self.prize_manager.get_prizes())


def main() -> int:
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (InputClosed, KeyboardInterrupt):
        print("\nInput closed. Exiting.")
    return 0
