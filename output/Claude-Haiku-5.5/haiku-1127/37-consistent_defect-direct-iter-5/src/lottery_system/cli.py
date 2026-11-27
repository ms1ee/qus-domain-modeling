"""Command-line interaction for the lottery system."""

from __future__ import annotations

import re

from .constants import PRESET_DRAWERS
from .models import User, normalize_text
from .services.list_manager import ListManager
from .services.lottery_manager import LotteryManager
from .services.prize_manager import PrizeManager
from .services.result_manager import ResultManager


def ordinal(number: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def parse_int_list(text: str):
    """Parse '2, 1 3' into [2, 1, 3]. Returns None if any token is not an integer."""
    tokens = [token for token in re.split(r"[,\s]+", text.strip()) if token]
    if not tokens:
        return None
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


class LotteryApp:
    """Interactive console application."""

    MENU = (
        "\n========== Team Building Smart Lottery ==========\n"
        "1. Load participant list\n"
        "2. Configure prizes\n"
        "3. Start lottery\n"
        "4. View / export results\n"
        "0. Exit"
    )

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.results: ResultManager | None = None
        self.lottery_prizes = []

    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            print(self.MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self.configure_prizes()
            elif choice == "3":
                self.start_lottery()
            elif choice == "4":
                self.view_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------------ list management
    def load_participants(self) -> None:
        print("\n--- Load Participant List ---")
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (format per line: Name,Department)")
        print("0. Back")
        choice = self._ask("Select: ")

        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        if errors:
            print(f"\nFound {len(errors)} problem(s) in the list:")
            for error in errors:
                print(f"  - {error}")
            decision = self._ask(
                "[R] Remove invalid data and continue / [T] Terminate upload: "
            ).lower()
            if decision != "r":
                print("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
            decision = self._ask(
                "[R] Remove duplicate entries and continue / [T] Terminate upload: "
            ).lower()
            if decision != "r":
                print("Upload terminated.")
                return

        if not valid:
            print("No valid participants found. List not loaded.")
            return

        self.users = valid
        print(f"Loaded {len(self.users)} participant(s).")
        self._show_groups()

    def _show_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        print("\nDepartment groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} people")

    # ---------------------------------------------------------- prize management
    def configure_prizes(self) -> None:
        while True:
            prizes = self.prize_manager.get_prizes()
            print("\n--- Prize Configuration ---")
            if prizes:
                for index, prize in enumerate(prizes, start=1):
                    print(self._format_prize(index, prize))
            else:
                print("(no prizes configured)")
            print("1. Load preset prizes")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Reorder lottery sequence")
            print("0. Back")
            choice = self._ask("Select: ")

            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(error)
                if not errors:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    @staticmethod
    def _format_prize(index: int, prize) -> str:
        drawer = prize.associated_drawer or "-"
        groups = ", ".join(prize.avoid_groups) or "-"
        return (f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoidance groups: {groups}")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) <= 0:
            print("Quantity must be a positive integer.")
            return
        quantity = int(quantity_text)

        groups: list[str] = []
        if self.users:
            groups = self._choose_groups()
        else:
            print("No participant list loaded; avoidance groups skipped.")

        drawer = self._choose_drawer()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")

    def _choose_groups(self) -> list[str]:
        info = self.list_manager.get_group_info(self.users)
        names = list(info.keys())
        print("Department groups:")
        for index, name in enumerate(names, start=1):
            print(f"  {index}. {name} ({info[name]} people)")
        text = self._ask("Enter group numbers (comma separated), or press Enter for none: ")
        return self._parse_groups(text, names)

    @staticmethod
    def _parse_groups(text: str, names: list[str]) -> list[str]:
        selected: list[str] = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            chosen = None
            if token.isdigit() and 1 <= int(token) <= len(names):
                chosen = names[int(token) - 1]
            else:
                for name in names:
                    if normalize_text(name) == normalize_text(token):
                        chosen = name
                        break
            if chosen is None:
                print(f"Ignored unknown group: {token}")
            elif chosen not in selected:
                selected.append(chosen)
        return selected

    def _choose_drawer(self):
        print("Associated lottery person:")
        print("  0. None")
        for index, person in enumerate(PRESET_DRAWERS, start=1):
            print(f"  {index}. {person}")
        other_index = len(PRESET_DRAWERS) + 1
        print(f"  {other_index}. Other (type name)")
        choice = self._ask("Select: ")

        if choice in ("", "0"):
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(PRESET_DRAWERS):
            return PRESET_DRAWERS[int(choice) - 1]
        if choice == str(other_index):
            return self._ask("Enter lottery person name: ") or None
        return choice

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(self._format_prize(index, prize))
        choice = self._ask("Prize number: ")
        if not choice.isdigit() or not 1 <= int(choice) <= len(prizes):
            print("Invalid prize number.")
            return
        if not self.users:
            print("Load participant list first.")
            return
        groups = self._choose_groups()
        if self.prize_manager.set_avoid_groups(int(choice) - 1, groups):
            print("Avoidance groups updated.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(self._format_prize(index, prize))
        order = parse_int_list(
            self._ask("Enter new order as serial numbers (e.g. 2,1,3): ")
        )
        if order is None:
            print("Invalid input. Please enter serial numbers separated by commas.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ------------------------------------------------------------- lottery flow
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first (option 1).")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first (option 2).")
            return

        lottery = LotteryManager(self.users)
        results = ResultManager()
        print("\n========== Lottery Started ==========")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, len(prizes), prize, lottery, results)

        self.results = results
        self.lottery_prizes = prizes
        print("\n========== All Rounds Completed ==========")
        self._print_summary(results, prizes)

    def _await_action(self) -> str:
        """Return 'draw' or 'terminate' according to operator commands."""
        while True:
            command = self._ask(
                "[Enter/continue] draw next | pause | terminate: "
            ).lower()
            if command in ("", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("(paused) > ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        break
                    if resume == "terminate":
                        return "terminate"
                    print("Unknown command. Use 'continue' or 'terminate'.")
                continue
            print("Unknown command.")

    def _run_round(self, round_no, total, prize, lottery: LotteryManager,
                   results: ResultManager) -> None:
        print(f"\n===== Round {round_no}/{total}: {prize.name} =====")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        drawn: list[User] = []
        while len(drawn) < prize.quantity:
            action = self._await_action()
            if action == "terminate":
                print("Round terminated. Remaining draws for this prize are skipped.")
                break

            print(f"Currently drawing the {ordinal(len(drawn) + 1)} winner...")
            winner = lottery.draw_winner(prize)
            if winner is None:
                print("No eligible candidates remain for this prize. Round ends.")
                break

            results.add_winner(winner, prize)
            drawn.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) "
                  f"for winning {prize.name}!")

        self._print_round_results(prize, drawn)

    @staticmethod
    def _print_round_results(prize, winners: list[User]) -> None:
        print(f"\nRound results for {prize.name} (winning order):")
        if not winners:
            print("  No winners in this round.")
            return
        for index, user in enumerate(winners, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    @staticmethod
    def _print_summary(results: ResultManager, prizes) -> None:
        winners = results.get_ordered_winners(prizes)
        if not winners:
            print("No winners were recorded.")
            return
        print("\nComplete winner list (by prize level, then winning order):")
        print(f"{'No.':<5}{'Name':<16}{'Department':<30}Prize Name")
        for index, record in enumerate(winners, start=1):
            print(f"{index:<5}{record.user.name:<16}{record.user.department:<30}"
                  f"{record.prize_name}")

    # ---------------------------------------------------------------- results
    def view_results(self) -> None:
        if self.results is None:
            print("No lottery has been run yet.")
            return
        while True:
            print("\n--- Results ---")
            print("1. Show winner list")
            print("2. Export winner list to txt (CSV format)")
            print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                self._print_summary(self.results, self.lottery_prizes)
            elif choice == "2":
                _, message = self.results.export_to_csv(self.lottery_prizes)
                print(message)
            elif choice == "0":
                return
            else:
                print("Invalid option.")


def main() -> None:
    app = LotteryApp()
    try:
        app.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
