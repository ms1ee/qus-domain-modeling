"""Command-line interface for the team building lottery system."""

from __future__ import annotations

from typing import Callable

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


def ordinal(n: int) -> str:
    """Return the English ordinal form of n, e.g. 1st, 2nd, 11th."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def parse_int_list(text: str) -> list[int] | None:
    """Parse integers separated by spaces or commas. Returns None on invalid input."""
    tokens = text.replace(",", " ").split()
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


class LotteryApp:
    """Interactive command-line application controller."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._output = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery_manager: LotteryManager | None = None

    # ------------------------------------------------------------------ helpers
    def _say(self, message: str = "") -> None:
        self._output(message)

    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _confirm(self, prompt: str) -> bool:
        return self._ask(f"{prompt} (y/n): ").strip().lower() in ("y", "yes")

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    # --------------------------------------------------------------- main loop
    def run(self) -> int:
        self._say("=== Company Team Building Smart Lottery System ===")
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.show_results()
            elif choice == "0":
                self._say("Goodbye!")
                return 0
            else:
                self._say("Invalid option, please try again.")

    def _print_main_menu(self) -> None:
        self._say("\n--- Main Menu ---")
        self._say("  1. Load participant list")
        self._say("  2. View department groups")
        self._say("  3. Prize configuration")
        self._say("  4. Start lottery")
        self._say("  5. View / export results")
        self._say("  0. Exit")

    # ------------------------------------------------------- participant list
    def load_participants(self) -> None:
        self._say("\nSelect list source:")
        self._say("  1. Built-in default team building list")
        self._say("  2. Custom txt file (each line: Name,Department Group)")
        self._say("  0. Cancel")
        choice = self._ask("Choice: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        valid = self._review_import(users, errors)
        if valid is None:
            self._say("Upload terminated. Participant list unchanged.")
            return
        self.users = valid
        self._say(f"Participant list loaded: {len(valid)} participants.")

    def _review_import(self, users: list[User], errors: list[str]) -> list[User] | None:
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            if not valid:
                self._say("No participants found in the list.")
                return None
            return valid

        self._say("\nIssues found in the list:")
        for error in errors:
            self._say(f"  - {error}")
        for dup in duplicates:
            self._say(f"  - Duplicate name: {dup.name} ({dup.department}) - later entry ignored")
        self._say(f"Valid participants: {len(valid)}")
        self._say("Options:")
        self._say("  1. Remove all invalid and duplicate entries and continue")
        self._say("  2. Manually remove specific participants by name, then continue")
        self._say("  3. Terminate upload")
        choice = self._ask("Choice: ").strip()

        if choice == "1":
            result = valid
        elif choice == "2":
            text = self._ask("Enter names to remove (comma separated): ")
            to_remove = {name.strip() for name in text.split(",") if name.strip()}
            result = [user for user in valid if user.name not in to_remove]
        else:
            return None

        if not result:
            self._say("No valid participants remain.")
            return None
        return result

    def show_groups(self) -> None:
        if not self.users:
            self._say("No participant list loaded. Please load a list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say("Current valid department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._say(f"  {index}. {department}: {count} people")
        self._say(f"Total: {len(self.users)} people")

    # ---------------------------------------------------------- prize config
    def prize_menu(self) -> None:
        while True:
            self._say("\n--- Prize Configuration ---")
            self._print_prizes()
            self._say("  1. Load preset prizes")
            self._say("  2. Add custom prize")
            self._say("  3. Change lottery order")
            self._say("  0. Back")
            choice = self._ask("Choice: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._say(f"  - {error}")
                else:
                    self._say("Preset prizes loaded.")
            elif choice == "2":
                self.add_prize()
            elif choice == "3":
                self.reorder_prizes()
            elif choice == "0":
                return
            else:
                self._say("Invalid option, please try again.")

    def _print_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("  (no prizes configured)")
            return
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._say(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {avoid} | lottery person: {drawer}"
            )

    def _select_avoid_groups(self) -> list[str] | None:
        groups = self._group_names()
        if not groups:
            self._say("Load the participant list first to select avoid groups; no avoid groups set.")
            return []
        self._say("Department groups:")
        for index, group in enumerate(groups, start=1):
            self._say(f"  {index}. {group}")
        text = self._ask("Select groups to avoid by number (comma separated, blank for none): ").strip()
        if not text:
            return []
        numbers = parse_int_list(text)
        if numbers is None or any(n < 1 or n > len(groups) for n in numbers):
            self._say("Invalid group selection.")
            return None
        return list(dict.fromkeys(groups[n - 1] for n in numbers))

    def add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._say("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be a positive integer.")
            return
        avoid_groups = self._select_avoid_groups()
        if avoid_groups is None:
            return
        drawer = self._ask("Associated lottery person (blank for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            self._say(f"Failed to add prize: {exc}")
            return
        self._say("Prize added.")

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            self._say("At least two prizes are needed to change the order.")
            return
        text = self._ask(
            f"Enter new order as serial numbers 1-{len(prizes)} (e.g. 2 1 3): "
        )
        order = parse_int_list(text)
        if order is None or not self.prize_manager.reorder_prizes(order):
            self._say("Invalid order. Each serial number from 1 to N must appear exactly once.")
            return
        self._say("Lottery order updated.")

    # ----------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users:
            self._say("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("Please configure prizes first.")
            return
        if self.lottery_manager and self.lottery_manager.result_manager.get_winners():
            if not self._confirm("A previous lottery has results. Starting a new lottery clears them. Continue"):
                return

        self.lottery_manager = LotteryManager(self.users)
        self._say("\n=== Lottery started ===")
        self._say("Commands: [Enter] draw next winner | pause | terminate (end current round)")
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
        self._say("\n=== Lottery finished ===")
        self.show_results()

    def _run_round(self, index: int, total: int, prize) -> None:
        manager = self.lottery_manager
        assert manager is not None
        self._say(f"\n--- Round {index}/{total}: {prize.name} ---")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rules: {manager.describe_rules(prize)}")

        round_winners = []
        while len(round_winners) < prize.quantity:
            position = len(round_winners) + 1
            command = self._ask(
                f"[{ordinal(position)} winner] Press Enter to draw, or type pause/terminate: "
            ).strip().lower()

            if command == "pause":
                if not self._pause_round():
                    self._say("Round terminated by operator.")
                    break
                continue
            if command == "terminate":
                self._say("Round terminated by operator.")
                break
            if command:
                self._say(f"Unknown command '{command}'.")
                continue

            self._say(f"Currently drawing the {ordinal(position)} winner...")
            winner = manager.draw_one(prize)
            if winner is None:
                self._say("No eligible participants remain for this prize. Round ends.")
                break
            round_winners.append(winner)
            self._say(
                f"Congratulations {winner.user.name} ({winner.user.department}) "
                f"for winning {prize.name}!"
            )

        self._say(f"Round {index} results (in winning order):")
        if not round_winners:
            self._say("  (no winners)")
        for position, winner in enumerate(round_winners, start=1):
            self._say(f"  {ordinal(position)}: {winner.user.name} ({winner.user.department})")

    def _pause_round(self) -> bool:
        """Pause until 'continue' (returns True) or 'terminate' (returns False)."""
        self._say("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._ask("(paused) > ").strip().lower()
            if command == "continue":
                self._say("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._say("Only 'continue' or 'terminate' is accepted while paused.")

    # ----------------------------------------------------------------- results
    def show_results(self) -> None:
        if not self.lottery_manager or not self.lottery_manager.result_manager.get_winners():
            self._say("No results yet.")
            return
        result_manager = self.lottery_manager.result_manager
        prizes = self.prize_manager.get_prizes()
        by_prize = result_manager.get_winners_by_prize(prizes)

        self._say("\n=== Winner List ===")
        for prize_name, winners in by_prize.items():
            self._say(f"{prize_name}:")
            if not winners:
                self._say("  (no winners)")
            for winner in winners:
                self._say(f"  - {winner.user.name} ({winner.user.department})")

        if self._confirm("Export results to a CSV-formatted txt file"):
            _, message = result_manager.export_to_csv(prizes)
            self._say(message)


def main(argv: list[str] | None = None) -> int:
    """Program entry point."""
    app = LotteryApp()
    try:
        return app.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return 0
