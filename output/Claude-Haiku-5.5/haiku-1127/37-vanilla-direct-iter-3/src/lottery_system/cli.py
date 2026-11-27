"""Command-line interface for the company team building smart lottery system."""

from __future__ import annotations

import queue
import sys
import threading

from lottery_system.config import DRAW_INTERVAL_SECONDS
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class InputReader:
    """Reads stdin lines in a background thread so commands can be polled during a lottery."""

    _EOF = object()

    def __init__(self, stream=None) -> None:
        self._stream = stream or sys.stdin
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._pump, name="stdin-reader", daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        while True:
            try:
                line = self._stream.readline()
            except (OSError, ValueError):
                line = ""
            if not line:
                self._queue.put(self._EOF)
                return
            self._queue.put(line.rstrip("\r\n"))

    def read(self, timeout: float | None = None) -> str | None:
        """Return the next line. Returns None on timeout. Raises EOFError at end of input."""
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        if item is self._EOF:
            self._queue.put(self._EOF)
            raise EOFError("End of input reached.")
        return item


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Menu-driven controller for the whole lottery process."""

    def __init__(self, reader: InputReader | None = None) -> None:
        self._reader = reader or InputReader()
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._result_manager = ResultManager()
        self._lottery: LotteryManager | None = None
        self._users: list[User] = []
        self._drawn_prizes: set[str] = set()
        self._menu = [
            ("1", "Load built-in default team building list", self._load_default_list),
            ("2", "Upload custom TXT list (Name,Department per line)", self._upload_custom_list),
            ("3", "View department groups and headcount", self._show_groups),
            ("4", "Load preset prize library", self._load_default_prizes),
            ("5", "Add custom prize", self._add_custom_prize),
            ("6", "Set avoidance groups for a prize", self._configure_avoid_groups),
            ("7", "Set associated lottery person for a prize", self._configure_drawer),
            ("8", "View prize list and lottery order", self._show_prizes),
            ("9", "Reorder prizes (lottery sequence)", self._reorder_prizes),
            ("10", "Start lottery", self._start_lottery),
            ("11", "View final results", self._view_final_results),
            ("12", "Export results to TXT (CSV format)", self._export_results),
        ]
        self._actions = {key: action for key, _, action in self._menu}

    # ------------------------------------------------------------------ basics
    def _println(self, text: str = "") -> None:
        print(text, flush=True)

    def _prompt(self, text: str) -> str:
        sys.stdout.write(text)
        sys.stdout.flush()
        line = self._reader.read()
        return line if line is not None else ""

    def _ask_positive_int(self, text: str) -> int:
        while True:
            raw = self._prompt(text).strip()
            try:
                value = int(raw)
            except ValueError:
                value = 0
            if value > 0:
                return value
            self._println("Please enter a positive integer.")

    def _ask_index(self, text: str, count: int) -> int | None:
        """Ask for a 1-based index. Blank input cancels (returns None)."""
        while True:
            raw = self._prompt(text).strip()
            if not raw:
                return None
            if raw.isdigit() and 1 <= int(raw) <= count:
                return int(raw) - 1
            self._println(f"Please enter a number between 1 and {count}, or press Enter to cancel.")

    def run(self) -> None:
        self._println("=" * 64)
        self._println("  Company Team Building - Smart Lottery System")
        self._println("=" * 64)
        while True:
            self._show_menu()
            choice = self._prompt("Select an option: ").strip()
            if choice == "0":
                self._println("Goodbye!")
                return
            action = self._actions.get(choice)
            if action is None:
                self._println("Invalid option, please try again.")
                continue
            action()

    def _show_menu(self) -> None:
        self._println("")
        self._println("---------------------- MENU ----------------------")
        for key, label, _ in self._menu:
            self._println(f"  {key:>2}. {label}")
        self._println("   0. Exit")

    # ------------------------------------------------------------ list module
    def _load_default_list(self) -> None:
        users, errors = self._list_manager.load_default_list()
        self._accept_users(users, errors)

    def _upload_custom_list(self) -> None:
        path = self._prompt("Enter the path of the TXT file: ").strip().strip('"')
        if not path:
            self._println("No path entered. Upload cancelled.")
            return
        users, errors = self._list_manager.load_custom_list(path)
        self._accept_users(users, errors)

    def _accept_users(self, users: list[User], errors: list[str]) -> bool:
        if errors:
            self._println(f"Found {len(errors)} invalid line(s):")
            for error in errors:
                self._println(f"  - {error}")
            if not users:
                self._println("No valid records found. Upload terminated.")
                return False
            answer = self._prompt(
                "Enter R to remove the invalid lines and continue, or T to terminate the upload: "
            )
            if answer.strip().lower() != "r":
                self._println("Upload terminated.")
                return False
            self._println(f"Invalid lines removed; {len(users)} valid record(s) kept.")

        valid, duplicates = self._list_manager.validate_users(users)
        if duplicates:
            self._println(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                self._println(f"  - {user.name} ({user.department})")
            answer = self._prompt(
                "Enter K to keep the first occurrence and remove duplicates, or T to terminate: "
            )
            if answer.strip().lower() != "k":
                self._println("Upload terminated.")
                return False

        self._set_users(valid)
        return True

    def _set_users(self, users: list[User]) -> None:
        had_results = bool(self._result_manager.get_winners())
        self._users = list(users)
        self._result_manager = ResultManager()
        self._lottery = None
        self._drawn_prizes = set()
        self._println(f"Loaded {len(self._users)} participant(s).")
        if had_results:
            self._println("Note: previous lottery results were cleared because the list changed.")
        self._show_groups()

    def _group_names(self) -> list[str]:
        if not self._users:
            return []
        return list(self._list_manager.get_group_info(self._users).keys())

    def _show_groups(self) -> None:
        if not self._users:
            self._println("No participant list loaded.")
            return
        info = self._list_manager.get_group_info(self._users)
        self._println("Department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._println(f"  {index}. {department}: {count} person(s)")
        self._println(f"Total participants: {len(self._users)}")

    # ----------------------------------------------------------- prize module
    def _load_default_prizes(self) -> None:
        errors = self._prize_manager.load_default_prizes()
        for error in errors:
            self._println(f"Warning: {error}")
        self._println("Preset prize library loaded.")
        self._show_prizes()

    def _show_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            self._println("No prizes configured yet.")
            return
        self._println("Prize list (lottery order):")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "-"
            status = " [drawn]" if prize.name in self._drawn_prizes else ""
            self._println(
                f"  {index}. {prize.name} | Qty: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {groups}{status}"
            )

    def _resolve_groups(self, text: str, groups: list[str]) -> list[str]:
        selected: list[str] = []
        for token in (part.strip() for part in text.split(",")):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                value = groups[int(token) - 1]
            else:
                match = next((g for g in groups if g.casefold() == token.casefold()), None)
                value = match or token
            if value not in selected:
                selected.append(value)
        return selected

    def _select_groups(self) -> list[str]:
        groups = self._group_names()
        if groups:
            self._println("Available department groups:")
            for index, group in enumerate(groups, start=1):
                self._println(f"  {index}. {group}")
        else:
            self._println("No participant list loaded; you may type group names directly.")
        text = self._prompt(
            "Avoidance groups (numbers or names, comma-separated; blank for none): "
        )
        return self._resolve_groups(text, groups)

    def _add_custom_prize(self) -> None:
        name = self._prompt("Prize name: ").strip()
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self._prompt(
            "Associated lottery person (blank for none; e.g. Chen Qixian / Jin Duo / "
            "Ma Jiaqi / Li Bin): "
        ).strip() or None
        groups = self._select_groups()
        try:
            prize = self._prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._println(f"Error: {exc}")
            return
        self._println(
            f"Prize added: {prize.name} (Qty: {prize.quantity}, "
            f"Lottery person: {prize.associated_drawer or '-'}, "
            f"Avoid groups: {', '.join(prize.avoid_groups) or '-'})"
        )

    def _choose_prize(self) -> Prize | None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            self._println("No prizes configured yet.")
            return None
        self._show_prizes()
        index = self._ask_index("Select prize number (Enter to cancel): ", len(prizes))
        return None if index is None else prizes[index]

    def _configure_avoid_groups(self) -> None:
        prize = self._choose_prize()
        if prize is None:
            return
        groups = self._select_groups()
        if self._prize_manager.set_avoid_groups(prize.name, groups):
            self._println(
                f"Avoidance groups for '{prize.name}': {', '.join(groups) or '-'}"
            )

    def _configure_drawer(self) -> None:
        prize = self._choose_prize()
        if prize is None:
            return
        drawer = self._prompt(
            "Associated lottery person (blank to clear): "
        ).strip() or None
        if self._prize_manager.set_associated_drawer(prize.name, drawer):
            self._println(f"Lottery person for '{prize.name}': {drawer or '-'}")

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if len(prizes) < 2:
            self._println("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        raw = self._prompt(
            f"Enter the new order as serial numbers (1-{len(prizes)}), "
            "separated by spaces or commas: "
        )
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            self._println("Invalid input: please enter serial numbers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            self._println("Prize order updated.")
            self._show_prizes()
        else:
            self._println(
                f"Invalid order: each serial number from 1 to {len(prizes)} must appear exactly once."
            )

    # -------------------------------------------------------- lottery control
    def _start_lottery(self) -> None:
        if not self._users:
            self._println("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            self._println("Please configure prizes first.")
            return
        pending = [prize for prize in prizes if prize.name not in self._drawn_prizes]
        if not pending:
            self._println("All prizes have already been drawn.")
            return

        answer = self._prompt(f"Start the lottery for {len(pending)} round(s)? (y/n): ")
        if answer.strip().lower() != "y":
            self._println("Lottery cancelled.")
            return

        if self._lottery is None:
            self._lottery = LotteryManager(self._users)

        self._println("Lottery started. Commands: pause | continue | terminate")
        names = [prize.name for prize in prizes]
        for prize in pending:
            round_no = names.index(prize.name) + 1
            self._run_round(self._lottery, prize, round_no, len(prizes))

        self._println("")
        self._println("All rounds completed.")
        self._show_final_results()

    def _read_command(self, timeout: float | None) -> str | None:
        line = self._reader.read(timeout)
        return None if line is None else line.strip()

    def _run_round(self, lottery: LotteryManager, prize: Prize, round_no: int, total: int) -> None:
        self._println("")
        self._println(f"=== Round {round_no}/{total}: {prize.name} ===")
        self._println(f"Quantity: {prize.quantity}")
        self._println(f"Lottery person: {prize.associated_drawer or '-'}")
        self._println(f"Rules: {lottery.describe_rules(prize)}")
        self._println(f"Eligible candidates: {lottery.get_eligible_count(prize)}")

        lottery.begin_round(prize)
        round_winners = []
        paused = False
        terminated = False

        while len(round_winners) < prize.quantity:
            if paused:
                command = self._read_command(None)
            else:
                self._println(
                    f"Currently drawing the {_ordinal(len(round_winners) + 1)} winner..."
                )
                command = self._read_command(DRAW_INTERVAL_SECONDS)

            if command is not None:
                action = command.lower()
                if action == "pause":
                    if paused:
                        self._println("Lottery is already paused.")
                    else:
                        paused = True
                        self._println(
                            "[PAUSED] Type 'continue' to resume or 'terminate' to skip this round."
                        )
                elif action == "continue":
                    if paused:
                        paused = False
                        self._println("[RESUMED] Lottery continues.")
                    else:
                        self._println("Lottery is already running.")
                elif action == "terminate":
                    terminated = True
                    self._println("[TERMINATED] Skipping the remaining winners of this round.")
                    break
                elif action:
                    self._println(
                        f"Unknown command '{command}'. Use pause / continue / terminate."
                    )
                continue

            user = lottery.draw_one(prize)
            if user is None:
                self._println("No eligible candidates left for this prize; round ends early.")
                break
            round_winners.append(self._result_manager.add_winner(user, prize))
            self._println(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}!"
            )

        lottery.end_round(prize)
        self._drawn_prizes.add(prize.name)

        if terminated:
            self._println("Round ended by operator.")
        elif len(round_winners) < prize.quantity:
            self._println(
                f"Only {len(round_winners)} of {prize.quantity} winner(s) could be drawn."
            )

        self._println(f"Round results for {prize.name}:")
        if not round_winners:
            self._println("  (no winners)")
        for index, winner in enumerate(round_winners, start=1):
            self._println(f"  {index}. {winner.user.name} ({winner.user.department})")

    # ---------------------------------------------------------------- results
    def _show_final_results(self) -> None:
        prizes = self._prize_manager.get_prizes()
        by_prize = self._result_manager.get_winners_by_prize(prizes)
        self._println("=== Final Results (prize level high to low) ===")
        for prize_name, winners in by_prize.items():
            self._println(f"[{prize_name}]")
            if not winners:
                self._println("  (no winners)")
            for index, winner in enumerate(winners, start=1):
                self._println(f"  {index}. {winner.user.name} ({winner.user.department})")

    def _view_final_results(self) -> None:
        if not self._result_manager.get_winners():
            self._println("No results yet.")
            return
        self._show_final_results()

    def _export_results(self) -> None:
        if not self._result_manager.get_winners():
            self._println("No winners recorded yet; exporting header only.")
        _, message = self._result_manager.export_to_csv(self._prize_manager.get_prizes())
        self._println(message)


def main() -> int:
    cli = LotteryCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.", flush=True)
    return 0
