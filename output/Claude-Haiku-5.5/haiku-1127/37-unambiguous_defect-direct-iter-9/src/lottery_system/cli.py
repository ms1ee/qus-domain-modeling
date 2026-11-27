"""Command-line interaction for the lottery system."""
from __future__ import annotations

from collections import Counter
from typing import Callable

from lottery_system.models import Prize, User, sort_prizes_by_level
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager

SEPARATOR = "=" * 60


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _ci(text: str) -> str:
    return text.strip().casefold()


class LotteryCLI:
    """Interactive console application."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        self._print("Welcome to the Company Team Building Smart Lottery System")
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self.load_list()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.results_menu()
            elif choice == "0":
                self._print("Goodbye!")
                return
            else:
                self._print("Invalid option, please try again.")

    def _print_main_menu(self) -> None:
        self._print(SEPARATOR)
        self._print("1. Load participant list")
        self._print("2. View department groups")
        self._print("3. Prize configuration")
        self._print("4. Start lottery")
        self._print("5. View results / export")
        self._print("0. Exit")
        self._print(SEPARATOR)

    # ----- list management -----------------------------------------------
    def load_list(self) -> None:
        self._print("1. Built-in default team building list")
        self._print("2. Upload custom txt list (format: Name,Department per line)")
        self._print("0. Cancel")
        choice = self._ask("Your choice: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"')
            if not path:
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        resolved = self._resolve_list_issues(users, errors)
        if resolved is None:
            self._print("Upload terminated. Previous participant list is kept.")
            return
        if not resolved:
            self._print("No valid participants were loaded.")
            return
        self.users = resolved
        self.lottery = None
        self._print(f"Loaded {len(resolved)} participants.")
        self.show_groups()

    def _resolve_list_issues(
        self, users: list[User], errors: list[str]
    ) -> list[User] | None:
        """Interactively resolve format errors and duplicate names. None means cancelled."""
        while True:
            valid, duplicates = self.list_manager.validate_users(users)
            if not errors and not duplicates:
                return valid

            self._print("Data verification found issues:")
            for error in errors:
                self._print(f"  - {error}")
            for dup in duplicates:
                self._print(f"  - Duplicate name: {dup.name} ({dup.department})")
            self._print(
                "Options: [r] remove invalid and duplicate entries  "
                "[m] manually remove entries  [c] cancel upload"
            )
            choice = self._ask("Your choice: ").strip().lower()
            if choice == "r":
                return valid
            if choice == "m":
                counts = Counter(_ci(user.name) for user in users)
                self._print("Current entries:")
                for index, user in enumerate(users, start=1):
                    mark = "  [duplicate name]" if counts[_ci(user.name)] > 1 else ""
                    self._print(f"  {index}. {user.name} ({user.department}){mark}")
                raw = self._ask(
                    "Enter entry numbers to remove (comma separated, blank to skip): "
                )
                if not raw.strip():
                    continue
                tokens = raw.replace(",", " ").split()
                if not all(token.isdigit() for token in tokens) or any(
                    not 1 <= int(token) <= len(users) for token in tokens
                ):
                    self._print("Invalid entry numbers, nothing removed.")
                    continue
                to_remove = {int(token) for token in tokens}
                users = [
                    user for index, user in enumerate(users, start=1)
                    if index not in to_remove
                ]
                errors = []
                continue
            if choice == "c":
                return None
            self._print("Invalid choice.")

    def show_groups(self) -> None:
        if not self.users:
            self._print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("Valid department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._print(f"  {index}. {department}: {count} people")

    # ----- prize configuration -------------------------------------------
    def prize_menu(self) -> None:
        while True:
            self._print(SEPARATOR)
            self._print("Prize configuration")
            self._print("1. Load preset prize library")
            self._print("2. Add custom prize")
            self._print("3. View prizes")
            self._print("4. Adjust lottery order")
            self._print("0. Back")
            self._print(SEPARATOR)
            choice = self._ask("Your choice: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._print(f"Error: {error}")
                else:
                    self._print("Preset prizes loaded.")
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.show_prizes()
            elif choice == "4":
                self.adjust_order()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("Prizes in lottery order:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {groups} | Lottery person: {drawer}"
            )

    def add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._print("Cancelled.")
            return
        quantity = self._ask_positive_int("Quantity (blank to cancel): ")
        if quantity is None:
            self._print("Cancelled.")
            return
        drawer = self._ask("Associated lottery person (blank for none): ").strip() or None
        groups = self._select_avoid_groups()
        if groups is None:
            self._print("Cancelled.")
            return
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._print(f"Error: {exc}")
            return
        self._print(f"Prize '{name}' added.")

    def _ask_positive_int(self, prompt: str) -> int | None:
        while True:
            raw = self._ask(prompt).strip()
            if not raw:
                return None
            if raw.isdigit() and int(raw) >= 1:
                return int(raw)
            self._print("Please enter a positive integer (or leave blank to cancel).")

    def _select_avoid_groups(self) -> list[str] | None:
        if not self.users:
            self._print("No participant list loaded; enter group names manually.")
            raw = self._ask("Avoidance groups (comma separated, blank for none): ")
            return [token.strip() for token in raw.split(",") if token.strip()]

        groups = list(self.list_manager.get_group_info(self.users).keys())
        self._print("Available groups:")
        for index, group in enumerate(groups, start=1):
            self._print(f"  {index}. {group}")
        while True:
            raw = self._ask(
                "Select avoidance groups by number or name (comma separated, blank for none): "
            )
            tokens = [token.strip() for token in raw.split(",") if token.strip()]
            selected: list[str] = []
            unknown: str | None = None
            for token in tokens:
                if token.isdigit() and 1 <= int(token) <= len(groups):
                    match: str | None = groups[int(token) - 1]
                else:
                    match = next((g for g in groups if _ci(g) == _ci(token)), None)
                if match is None:
                    unknown = token
                    break
                if match not in selected:
                    selected.append(match)
            if unknown is not None:
                self._print(f"Unknown group: {unknown}. Please try again.")
                continue
            return selected

    def adjust_order(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self.show_prizes()
        raw = self._ask(
            "Enter new order as serial numbers, e.g. '2 1 3' (blank to cancel): "
        )
        if not raw.strip():
            return
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            self._print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Lottery order updated.")
            self.show_prizes()
        else:
            self._print("Invalid order: every serial number must appear exactly once.")

    # ----- lottery -------------------------------------------------------
    def start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return
        if self.lottery is not None and self.lottery.result_manager.get_winners():
            confirm = self._ask("Existing results will be cleared. Start a new lottery? (y/n): ")
            if confirm.strip().lower() != "y":
                return

        self.lottery = LotteryManager(self.users)
        self._print(SEPARATOR)
        self._print("LOTTERY START")
        self._print(SEPARATOR)
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, len(prizes), prize)
        self._print(SEPARATOR)
        self._print("All lottery rounds completed.")
        self.show_results()

    def _run_round(self, round_no: int, total_rounds: int, prize: Prize) -> None:
        assert self.lottery is not None
        self._print(SEPARATOR)
        self._print(f"Round {round_no}/{total_rounds}: {prize.name}")
        self._print(f"Quantity: {prize.quantity}")
        self._print(f"Rule: {self.lottery.describe_rule(prize)}")
        self._print(SEPARATOR)

        round_winners: list[User] = []
        terminated = False
        for position in range(1, prize.quantity + 1):
            if self.lottery.count_eligible(prize) == 0:
                self._print("No eligible candidates remain for this prize; round ends early.")
                break
            action = self._ask_draw_action()
            if action == "terminate":
                terminated = True
                break
            self._print(f"Currently drawing the {ordinal(position)} winner...")
            winner = self.lottery.draw_one(prize)
            if winner is None:
                self._print("No eligible candidates remain for this prize; round ends early.")
                break
            round_winners.append(winner)
            self._print(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}"
            )

        if terminated:
            skipped = prize.quantity - len(round_winners)
            self._print(f"Round terminated by operator; {skipped} award(s) skipped.")

        self.lottery.record_round_outcome(prize, round_winners)

        self._print(f"Current round results for {prize.name} (in winning order):")
        if not round_winners:
            self._print("  (no winners)")
        for index, winner in enumerate(round_winners, start=1):
            self._print(f"  {index}. {winner.name} ({winner.department})")

    def _ask_draw_action(self) -> str:
        """Return 'draw' or 'terminate'. Handles pause/continue commands."""
        prompt = "Press Enter to draw the next winner (or type 'pause' / 'terminate'): "
        while True:
            command = self._ask(prompt).strip().lower()
            if command in ("", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                self._print("Lottery paused.")
                while True:
                    resume = self._ask(
                        "Paused. Type 'continue' to resume or 'terminate' to end this round: "
                    ).strip().lower()
                    if resume == "continue":
                        self._print("Lottery resumed.")
                        return "draw"
                    if resume == "terminate":
                        return "terminate"
                    self._print("Unknown command.")
            self._print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # ----- results -------------------------------------------------------
    def show_results(self) -> None:
        if self.lottery is None or not self.lottery.result_manager.get_winners():
            self._print("No lottery results yet.")
            return
        prizes = sort_prizes_by_level(self.prize_manager.get_prizes())
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        self._print(SEPARATOR)
        self._print("WINNER LIST (by prize level, then winning order)")
        self._print(SEPARATOR)
        for prize in prizes:
            self._print(f"[{prize.name}]")
            winners = grouped[prize.name]
            if not winners:
                self._print("  (no winners)")
            for index, winner in enumerate(winners, start=1):
                self._print(f"  {index}. {winner.user.name} ({winner.user.department})")

    def results_menu(self) -> None:
        self.show_results()
        if self.lottery is None or not self.lottery.result_manager.get_winners():
            return
        choice = self._ask("Export results to awards_result_YYYYMMDD.txt? (y/n): ")
        if choice.strip().lower() != "y":
            return
        success, message = self.lottery.result_manager.export_to_csv(
            self.prize_manager.get_prizes()
        )
        self._print(message)


def main() -> None:
    app = LotteryCLI()
    try:
        app.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
