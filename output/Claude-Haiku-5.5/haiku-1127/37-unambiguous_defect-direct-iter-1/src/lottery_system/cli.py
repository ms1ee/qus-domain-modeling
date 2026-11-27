"""Command-line interface: list management, prize configuration, lottery control and results."""

from __future__ import annotations

import queue
import re
import sys
import threading
import time

from lottery_system.models import (
    CHEN_QIXIAN,
    DRAWER_CHOICES,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    Prize,
    User,
)
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAW_DELAY_SECONDS = 0.8
_EOF = object()


class InputReader:
    """Reads stdin in a background thread so lottery commands can be polled during draws."""

    def __init__(self, stream=None) -> None:
        self._stream = stream if stream is not None else sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._pump, name="stdin-reader", daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\r\n"))
        except (OSError, ValueError):
            pass
        self._queue.put(_EOF)

    def read_line(self, prompt: str = "") -> str:
        """Blocking read of one line (stripped)."""
        if prompt:
            print(prompt, end="", flush=True)
        item = self._queue.get()
        if item is _EOF:
            self._queue.put(_EOF)
            raise EOFError("Input closed")
        return item.strip()

    def poll(self) -> str | None:
        """Non-blocking read. Returns None when no input is pending."""
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item is _EOF:
            self._queue.put(_EOF)
            raise EOFError("Input closed")
        return item.strip()


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line application."""

    def __init__(self, reader: InputReader | None = None) -> None:
        self._reader = reader if reader is not None else InputReader()
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._results = ResultManager()
        self._last_prizes: list[Prize] | None = None

    def _ask(self, prompt: str) -> str:
        return self._reader.read_line(prompt)

    # ------------------------------------------------------------------ main
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building Smart Lottery System")
        print("=" * 60)
        while True:
            print(
                "\nMain Menu:\n"
                "  1. Manage participant list\n"
                "  2. View department groups\n"
                "  3. Configure prizes\n"
                "  4. Start lottery\n"
                "  5. Export last lottery results\n"
                "  0. Exit"
            )
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._list_menu()
            elif choice == "2":
                self._view_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "5":
                self._export_last_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------- list management
    def _list_menu(self) -> None:
        print(
            "\nParticipant List:\n"
            "  1. Load built-in default team building list\n"
            "  2. Upload custom txt list (format: name,department per line)\n"
            "  0. Back"
        )
        choice = self._ask("Select an option: ")
        if choice == "1":
            users, errors = self._list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"').strip("'")
            users, errors = self._list_manager.load_custom_list(path)
        else:
            return

        valid_users, duplicates = self._list_manager.validate_users(users)

        if not errors and not duplicates:
            self._users = valid_users
            print(f"Loaded {len(valid_users)} participant(s) successfully.")
            return

        print("\nVerification found problems:")
        for error in errors:
            print(f"  - {error}")
        for dup in duplicates:
            print(f"  - Duplicate name: '{dup.name}' ({dup.department}) ignored")
        print(f"Valid entries: {len(valid_users)}")
        print("Enter 'r' to remove invalid data and continue, or 't' to terminate the upload.")
        while True:
            answer = self._ask("Your choice (r/t): ").lower()
            if answer == "r":
                if not valid_users:
                    print("No valid entries remain. Upload terminated; previous list kept.")
                    return
                self._users = valid_users
                print(f"Invalid data removed. Loaded {len(valid_users)} participant(s).")
                return
            if answer == "t":
                print("Upload terminated; previous list kept.")
                return
            print("Please enter 'r' or 't'.")

    def _view_groups(self) -> None:
        if not self._users:
            print("No participant list loaded.")
            return
        groups = self._list_manager.get_group_info(self._users)
        print("\nDepartment groups:")
        for index, (department, count) in enumerate(groups.items(), start=1):
            print(f"  {index}. {department}: {count} people")

    def _current_group_names(self) -> list[str]:
        return list(self._list_manager.get_group_info(self._users).keys())

    # -------------------------------------------------------- prize config
    def _prize_menu(self) -> None:
        while True:
            print(
                "\nPrize Configuration:\n"
                "  1. Load preset prizes\n"
                "  2. Add custom prize\n"
                "  3. View prizes\n"
                "  4. Reorder prizes\n"
                "  0. Back"
            )
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self._prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  - {error}")
                print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _parse_groups(self, text: str) -> list[str]:
        groups_list = self._current_group_names()
        result: list[str] = []
        for token in re.split(r"[,，]", text):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups_list and 1 <= int(token) <= len(groups_list):
                value = groups_list[int(token) - 1]
            else:
                value = token
            if value not in result:
                result.append(value)
        return result

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be an integer.")
            return

        groups_list = self._current_group_names()
        if groups_list:
            print("Departments: " + ", ".join(f"{i}. {g}" for i, g in enumerate(groups_list, 1)))
        groups_text = self._ask(
            "Avoid groups (names or numbers, comma separated, blank for none): "
        )
        avoid_groups = self._parse_groups(groups_text)

        print("Lottery persons: " + ", ".join(f"{i}. {d}" for i, d in enumerate(DRAWER_CHOICES, 1)))
        drawer_text = self._ask("Associated lottery person (number or name, blank for none): ")
        drawer: str | None = None
        if drawer_text.isdigit() and 1 <= int(drawer_text) <= len(DRAWER_CHOICES):
            drawer = DRAWER_CHOICES[int(drawer_text) - 1]
        elif drawer_text:
            drawer = drawer_text

        try:
            self._prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize '{name.strip()}' added.")

    def _show_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {avoid} | lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (e.g. 2 1 3): "
        )
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self._show_prizes()
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ------------------------------------------------------------- lottery
    def _start_lottery(self) -> None:
        if not self._users:
            print("No participant list loaded. Please load a list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please configure prizes first.")
            return

        lottery = LotteryManager(self._users)
        self._results = ResultManager()
        self._last_prizes = prizes
        total = len(prizes)

        print("\n=== Lottery Start ===")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize, lottery)

        self._show_summary(prizes)
        if self._ask("Export results now? (y/n): ").lower() == "y":
            self._export_results(prizes)

    def _handle_commands(self) -> bool:
        """Process pending control commands. Returns True if the current round should end."""
        while True:
            command = self._reader.poll()
            if command is None:
                return False
            command = command.lower()
            if not command:
                continue
            if command == "pause":
                print("[PAUSED] Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    response = self._reader.read_line().lower()
                    if response == "continue":
                        print("[RESUMED]")
                        break
                    if response == "terminate":
                        return True
                    print("Type 'continue' or 'terminate'.")
            elif command == "terminate":
                return True
            elif command == "continue":
                print("Lottery is not paused.")
            else:
                print(f"Unknown command '{command}'. Use 'pause' or 'terminate'.")

    def _describe_rules(self, prize: Prize, lottery: LotteryManager) -> str:
        parts: list[str] = []
        drawer = prize.associated_drawer
        parts.append(f"Lottery person: {drawer}" if drawer else "Lottery person: none")
        if drawer == LI_BIN:
            parts.append("relaxed filtering (avoid groups not applied)")
        else:
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            parts.append(f"avoid groups: {avoid}")
        parts.append("previous winners excluded")
        if drawer == MA_JIAQI and lottery.is_fallback_active():
            parts.append("Cheng Ru Group protection ACTIVE: only Cheng Ru Group members eligible")
        return "; ".join(parts)

    def _run_round(self, index: int, total: int, prize: Prize, lottery: LotteryManager) -> None:
        print(f"\n--- Round {index}/{total}: {prize.name} ---")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {self._describe_rules(prize, lottery)}")
        answer = self._ask("Press Enter to start this round (type 'terminate' to skip): ")
        if answer.lower() == "terminate":
            print("Round skipped.")
            return

        print("Lottery in progress. Commands: 'pause', 'continue', 'terminate'.")
        round_winners: list[User] = []
        terminated = False
        for draw_no in range(1, prize.quantity + 1):
            if self._handle_commands():
                terminated = True
                break
            print(f"Currently drawing the {_ordinal(draw_no)} winner...", flush=True)
            time.sleep(DRAW_DELAY_SECONDS)
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize. Round ends early.")
                break
            round_winners.append(user)
            self._results.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        lottery.finish_round(prize, round_winners)
        if terminated:
            print("Round terminated manually. Remaining winners skipped.")

        print(f"\nRound {index} results ({len(round_winners)} winner(s)):")
        if not round_winners:
            print("  (none)")
        for position, user in enumerate(round_winners, start=1):
            print(f"  {position}. {user.name} ({user.department})")

    def _show_summary(self, prizes: list[Prize]) -> None:
        grouped = self._results.get_winners_by_prize(prizes)
        print("\n=== Final Winner List (by prize level) ===")
        for prize_name, winners in grouped.items():
            print(f"\n[{prize_name}] ({len(winners)} winner(s))")
            if not winners:
                print("  (none)")
            for position, winner in enumerate(winners, start=1):
                print(f"  {position}. {winner.user.name} ({winner.user.department})")

    # -------------------------------------------------------------- export
    def _export_results(self, prizes: list[Prize]) -> None:
        _, message = self._results.export_to_csv(prizes)
        print(message)

    def _export_last_results(self) -> None:
        if self._last_prizes is None:
            print("No lottery has been run yet.")
            return
        self._export_results(self._last_prizes)


def main() -> None:
    """Application entry point."""
    try:
        LotterySystemCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
