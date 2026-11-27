"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import Callable

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(number: int) -> str:
    """Return the English ordinal form of an integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line application."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery_manager: LotteryManager | None = None

    # ----- helpers -------------------------------------------------------

    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _set_users(self, users: list[User]) -> None:
        self.users = list(users)
        self.result_manager = ResultManager()
        self.lottery_manager = None

    # ----- main loop -----------------------------------------------------

    def run(self) -> None:
        self._print("=" * 50)
        self._print("  Team Building Smart Lottery System")
        self._print("=" * 50)
        while True:
            self._print("\n--- Main Menu ---")
            self._print("1. Load participant list")
            self._print("2. View department groups")
            self._print("3. Prize configuration")
            self._print("4. Start lottery")
            self._print("5. View winners")
            self._print("6. Export winner list")
            self._print("0. Exit")
            choice = self._ask("Select an option: ")

            if choice == "1":
                self._load_list_menu()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "5":
                self._show_winners()
            elif choice == "6":
                self._export()
            elif choice == "0":
                self._print("Goodbye!")
                return
            else:
                self._print("Invalid option, please try again.")

    # ----- participant list ----------------------------------------------

    def _load_list_menu(self) -> None:
        self._print("\n--- Load Participant List ---")
        self._print("1. Built-in default list")
        self._print("2. Custom txt file (format: Name,Department Group per line)")
        self._print("0. Cancel")
        choice = self._ask("Select an option: ")

        if choice == "1":
            users, _errors = self.list_manager.load_default_list()
            valid, _dups = self.list_manager.validate_users(users)
            self._set_users(valid)
            self._print(f"Loaded {len(valid)} participants from the built-in list.")
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            valid = self._handle_custom_load(path)
            if valid is None:
                return
            if not valid:
                self._print("No valid participants loaded.")
                return
            self._set_users(valid)
            self._print(f"Loaded {len(valid)} participants from '{path}'.")
        else:
            self._print("Cancelled.")

    def _handle_custom_load(self, path: str) -> list[User] | None:
        users, errors = self.list_manager.load_custom_list(path)
        valid, duplicates = self.list_manager.validate_users(users)

        if not errors and not duplicates:
            return valid

        self._print("\nIssues detected in the uploaded list:")
        for error in errors:
            self._print(f"  - {error}")
        for dup in duplicates:
            self._print(
                f"  - Duplicate Name: '{dup.name}' ({dup.department}) appears more "
                "than once; the later entry is ignored"
            )

        choice = self._ask(
            "Enter 'r' to remove invalid/duplicate entries and continue, "
            "'m' to manually remove names, 't' to terminate upload: "
        ).lower()

        if choice == "t":
            self._print("Upload terminated.")
            return None
        if choice == "m":
            names = self._ask("Enter names to remove (comma separated): ")
            to_remove = {name.strip() for name in names.split(",") if name.strip()}
            valid = [user for user in valid if user.name not in to_remove]
            return valid
        if choice == "r":
            return valid

        self._print("Invalid choice. Upload terminated.")
        return None

    def _show_groups(self) -> None:
        if not self.users:
            self._print("No participant list loaded. Please load a list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("\n--- Department Groups ---")
        for group, count in info.items():
            self._print(f"  {group}: {count} people")

    # ----- prize configuration -------------------------------------------

    def _prize_menu(self) -> None:
        while True:
            self._print("\n--- Prize Configuration ---")
            self._print("1. Load preset prizes")
            self._print("2. Add custom prize")
            self._print("3. Set avoidance groups / lottery person for a prize")
            self._print("4. Reorder prizes")
            self._print("5. View prizes")
            self._print("0. Back")
            choice = self._ask("Select an option: ")

            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._print(f"Error: {error}")
                self._print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_prize_rules()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._view_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def _select_groups(self) -> list[str]:
        if not self.users:
            self._print("(No participant list loaded; no avoidance groups available.)")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        self._print("Available department groups:")
        for idx, group in enumerate(groups, start=1):
            self._print(f"  {idx}. {group}")
        text = self._ask(
            "Select avoidance groups by number, comma separated (blank for none): "
        )
        selected: list[str] = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                group = groups[int(token) - 1]
                if group not in selected:
                    selected.append(group)
            else:
                self._print(f"Ignoring invalid group selection: '{token}'")
        return selected

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            self._print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            self._print("Quantity must be a positive integer.")
            return
        groups = self._select_groups()
        drawer = self._ask("Associated lottery person (leave blank for none): ") or None
        try:
            self.prize_manager.add_prize(name, int(quantity_text), groups, drawer)
            self._print(f"Prize '{name}' added.")
        except ValueError as exc:
            self._print(f"Failed to add prize: {exc}")

    def _set_prize_rules(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask("Select prize number to configure: ")
        if not text.isdigit() or not 1 <= int(text) <= len(prizes):
            self._print("Invalid prize number.")
            return
        index = int(text) - 1
        groups = self._select_groups()
        drawer = self._ask("Associated lottery person (leave blank for none): ") or None
        if self.prize_manager.update_prize(index, groups, drawer):
            self._print(f"Rules updated for '{prizes[index].name}'.")
        else:
            self._print("Failed to update prize.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (e.g. '2 1 3'): "
        )
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            self._print("Invalid input: please enter numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize order updated.")
            self._view_prizes()
        else:
            self._print(
                f"Invalid order: each number from 1 to {len(prizes)} must appear exactly once."
            )

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("\n--- Prize Sequence ---")
        for idx, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._print(
                f"  {idx}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {groups} | Lottery person: {drawer}"
            )

    # ----- lottery process -----------------------------------------------

    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured. Please configure prizes first.")
            return
        if self.lottery_manager is None:
            self.lottery_manager = LotteryManager(self.users)

        total = len(prizes)
        self._print("\n##### Lottery started #####")
        for idx, prize in enumerate(prizes, start=1):
            self._run_round(idx, total, prize)
        self._print("\n##### Lottery finished #####")
        self._show_winners()

    def _run_round(self, round_number: int, total: int, prize: Prize) -> None:
        assert self.lottery_manager is not None
        self._print(f"\n===== Round {round_number}/{total}: {prize.name} =====")
        self._print(f"Quantity: {prize.quantity}")
        self._print(f"Rules: {LotteryManager.describe_rules(prize)}")

        drawn: list[User] = []
        terminated = False

        while len(drawn) < prize.quantity and not terminated:
            command = self._ask(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).lower()

            if command == "pause":
                self._print("Lottery paused.")
                while True:
                    resume = self._ask(
                        "Type 'continue' to resume or 'terminate' to end this round: "
                    ).lower()
                    if resume == "continue":
                        self._print("Lottery resumed.")
                        break
                    if resume == "terminate":
                        terminated = True
                        break
                    self._print("Unknown command.")
                continue

            if command == "terminate":
                terminated = True
                break

            if command != "":
                self._print("Unknown command.")
                continue

            self._print(
                f"Currently drawing the {ordinal(len(drawn) + 1)} winner "
                f"for {prize.name}..."
            )
            user = self.lottery_manager.draw_winner(prize)
            if user is None:
                self._print("No eligible participants remain for this prize. Round ends.")
                break

            self.result_manager.add_winner(user, prize)
            drawn.append(user)
            self._print(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}"
            )

        if terminated:
            skipped = prize.quantity - len(drawn)
            self._print(f"Round terminated. {skipped} prize(s) skipped.")

        self._print(f"Round results for {prize.name}:")
        if not drawn:
            self._print("  (no winners in this round)")
        for position, user in enumerate(drawn, start=1):
            self._print(f"  {position}. {user.name} ({user.department})")

    def _show_winners(self) -> None:
        prizes = self.prize_manager.get_prizes()
        winners = self.result_manager.get_sorted_winners(prizes)
        if not winners:
            self._print("No winners yet.")
            return
        self._print("\n===== Complete Winner List =====")
        current_prize: str | None = None
        for winner in winners:
            if winner.prize_name != current_prize:
                current_prize = winner.prize_name
                self._print(f"\n{current_prize}:")
            self._print(
                f"  [{winner.winning_order}] {winner.user.name} "
                f"({winner.user.department}) - {winner.prize_name}"
            )

    def _export(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.result_manager.get_all_winners():
            self._print("No winners to export yet.")
            return
        _success, message = self.result_manager.export_to_csv(prizes)
        self._print(message)


def main() -> int:
    """Entry point for the command-line application."""
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
    return 0
