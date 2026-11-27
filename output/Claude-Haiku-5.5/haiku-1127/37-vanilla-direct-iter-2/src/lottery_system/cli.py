"""Command-line interface for the team building lottery system."""

from __future__ import annotations

import queue
import sys
import threading
import time

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager

DRAW_DELAY_SECONDS = 0.8


class InputHub:
    """Reads stdin in a background thread so commands can be checked while drawing."""

    _EOF = object()

    def __init__(self, stream=None):
        self._stream = stream or sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._eof = False
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while True:
            try:
                line = self._stream.readline()
            except (OSError, ValueError):
                line = ""
            if not line:
                self._queue.put(self._EOF)
                return
            self._queue.put(line.strip())

    def _convert(self, item):
        if item is self._EOF:
            self._eof = True
            raise EOFError
        return item

    def read_line(self) -> str:
        """Blocking read of the next input line."""
        if self._eof:
            raise EOFError
        return self._convert(self._queue.get())

    def poll(self) -> str | None:
        """Non-blocking read. Returns None when no line is waiting."""
        if self._eof:
            raise EOFError
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        return self._convert(item)


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive menu-driven controller."""

    def __init__(self, hub: InputHub | None = None):
        self.hub = hub or InputHub()
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list = []
        self.lottery: LotteryManager | None = None
        self.completed_prizes: set[str] = set()

    # ----- basic IO -----------------------------------------------------
    def _ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        return self.hub.read_line().strip()

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    def _print_main_menu(self):
        print("\n=== Main Menu ===")
        print("1. Load participant list")
        print("2. View department groups")
        print("3. Prize configuration")
        print("4. Start lottery")
        print("5. View winners")
        print("6. Export results (CSV in txt)")
        print("0. Exit")

    def run(self):
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        try:
            while True:
                self._print_main_menu()
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self._load_list()
                elif choice == "2":
                    self._view_groups()
                elif choice == "3":
                    self._prize_menu()
                elif choice == "4":
                    self._start_lottery()
                elif choice == "5":
                    self._show_summary()
                elif choice == "6":
                    self._export_results()
                elif choice == "0":
                    print("Goodbye!")
                    return
                else:
                    print("Invalid option, please try again.")
        except EOFError:
            print("\nInput closed. Exiting.")

    # ----- list management ----------------------------------------------
    def _load_list(self):
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (format: Name,Department Group per line)")
        print("0. Back")
        choice = self._ask("Select list source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path (empty to cancel): ")
            if not path:
                print("Upload cancelled.")
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        valid, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate name: {u.name} ({u.department}) - later entry ignored"
            for u in duplicates
        )
        if problems:
            print("Verification found the following issues:")
            for problem in problems:
                print(f"  - {problem}")
            print(f"Valid records: {len(valid)}")
            answer = self._ask(
                "Type 'remove' to discard invalid data and continue, "
                "or 'terminate' to abort the upload: "
            ).lower()
            if answer != "remove":
                print("Upload terminated. Current list unchanged.")
                return

        if not valid:
            print("No valid participants found. List not loaded.")
            return

        self.users = valid
        self.lottery = None
        self.completed_prizes = set()
        print(f"List loaded: {len(valid)} participant(s).")
        self._view_groups()

    def _view_groups(self):
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Valid department groups:")
        for index, (dept, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {dept}: {count} people")

    # ----- prize configuration ------------------------------------------
    def _prize_menu(self):
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes (lottery order)")
            print("4. Reorder prizes")
            print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _parse_groups(self, text: str, names: list[str]) -> list[str]:
        """Parse avoidance group selection by serial number or name."""
        if not text.strip():
            return []
        result: list[str] = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit():
                index = int(token)
                if not names or not 1 <= index <= len(names):
                    raise ValueError(f"Invalid group number: {token}")
                result.append(names[index - 1])
            elif names:
                match = next((g for g in names if g.casefold() == token.casefold()), None)
                if match is None:
                    raise ValueError(f"Unknown group: {token}")
                result.append(match)
            else:
                result.append(token)
        return list(dict.fromkeys(result))

    def _add_custom_prize(self):
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be an integer.")
            return
        drawer = self._ask("Associated lottery person (empty for none): ")

        names = self._group_names()
        if names:
            print("Department groups:")
            for index, group in enumerate(names, start=1):
                print(f"  {index}. {group}")
        text = self._ask(
            "Avoidance groups (serial numbers or names, comma-separated; empty for none): "
        )
        try:
            groups = self._parse_groups(text, names)
        except ValueError as exc:
            print(f"Failed: {exc}")
            return

        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer or None)
        except ValueError as exc:
            print(f"Failed: {exc}")
            return
        print(f"Prize '{name.strip()}' added.")

    def _view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "-"
            drawer = prize.associated_drawer or "-"
            print(
                f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {groups}"
            )

    def _reorder_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask("Enter new order as serial numbers, e.g. 2,1,3: ")
        try:
            order = [int(token) for token in text.split(",") if token.strip()]
        except ValueError:
            print("Invalid input: use integers separated by commas.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ----- lottery process ----------------------------------------------
    def _start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        pending = [p for p in prizes if p.name not in self.completed_prizes]
        if not pending:
            print("All prizes have already been drawn.")
            return

        print("Lottery starts. Commands during drawing: pause / continue / terminate")
        for prize in pending:
            self._run_round(prize)
        print("\nAll lottery rounds finished.")
        self._show_summary()

    def _run_round(self, prize):
        lottery = self.lottery
        print("\n" + "=" * 60)
        print(f"Round: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {lottery.describe_rule(prize)}")
        print("=" * 60)

        round_winners = []
        for position in range(1, prize.quantity + 1):
            print(f"Currently drawing the {_ordinal(position)} winner...", flush=True)
            if not self._checkpoint(DRAW_DELAY_SECONDS):
                print("Round terminated. Remaining draws skipped.")
                break
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize; the round ends early.")
                break
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        lottery.record_round(prize, round_winners)
        self.completed_prizes.add(prize.name)
        print(f"Round finished: {len(round_winners)}/{prize.quantity} winner(s) drawn.")
        for index, user in enumerate(round_winners, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    def _checkpoint(self, duration: float) -> bool:
        """Wait for the draw interval while handling control commands.

        Returns False if the current round must be terminated.
        """
        deadline = time.monotonic() + duration
        while True:
            command = self.hub.poll()
            if command is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True
                time.sleep(min(0.05, remaining))
                continue

            command = command.lower()
            if command == "pause":
                print("[PAUSED] Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    answer = self.hub.read_line().lower()
                    if answer == "continue":
                        print("[RESUMED]")
                        return True
                    if answer == "terminate":
                        print("[TERMINATED]")
                        return False
                    print("Type 'continue' or 'terminate'.")
            elif command == "terminate":
                print("[TERMINATED]")
                return False
            elif command == "continue":
                print("Lottery is not paused.")
            elif command == "":
                continue
            else:
                print("Unknown command. Available during lottery: pause, continue, terminate")

    # ----- results ------------------------------------------------------
    def _show_summary(self):
        if self.lottery is None:
            print("No lottery results yet.")
            return
        prizes = self.prize_manager.get_prizes()
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        print("\n=== Winner List (by prize level, then winning order) ===")
        if not any(grouped.values()):
            print("No winners yet.")
            return
        for prize_name, winners in grouped.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.order}. {winner.user.name} | "
                    f"{winner.user.department} | {prize_name}"
                )

    def _export_results(self):
        if self.lottery is None:
            print("No lottery results to export.")
            return
        success, message = self.lottery.result_manager.export_to_csv(
            self.prize_manager.get_prizes()
        )
        print(message)


def main():
    """Program entry point."""
    LotterySystemCLI().run()


if __name__ == "__main__":
    main()
