"""Command-line interface for the team building smart lottery system."""

from __future__ import annotations

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.lottery_process import LotteryProcess
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


MAIN_MENU = """
========== Team Building Smart Lottery ==========
1. Load participant list
2. View department groups
3. Prize configuration
4. Start lottery
5. View results and export
0. Exit
=================================================="""

PRIZE_MENU = """
---------- Prize Configuration ----------
1. List prizes
2. Load preset prizes
3. Add custom prize
4. Set avoidance groups / lottery person
5. Reorder lottery sequence
0. Back
-----------------------------------------"""


class LotteryCLI:
    """Interactive console controller."""

    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._output = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.list_source: str | None = None
        self.lottery_manager: LotteryManager | None = None
        self.result_manager: ResultManager | None = None
        self.lottery_prizes: list = []

    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _say(self, message: str = "") -> None:
        self._output(message)

    def run(self) -> None:
        self._say("Welcome to the Team Building Smart Lottery System.")
        while True:
            self._say(MAIN_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.results_menu()
            elif choice == "0":
                self._say("Goodbye!")
                return
            else:
                self._say("Invalid option, please try again.")

    # ----- participant list -----

    def load_participants(self) -> None:
        self._say("1. Built-in default list")
        self._say("2. Upload custom txt list (each line: Name,Department Group)")
        self._say("0. Back")
        choice = self._ask("Select a loading mode: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            source = "default"
        elif choice == "2":
            path = self._ask("Enter the path of the txt file: ")
            users, errors = self.list_manager.load_custom_list(path)
            source = "custom"
            if errors:
                self._say(f"Verification found {len(errors)} problem(s):")
                for error in errors:
                    self._say(f"  - {error}")
                self._say("Enter 'R' to remove the invalid data and continue with valid participants,")
                decision = self._ask("or 'T' to terminate the upload [R/T]: ").upper()
                if decision != "R":
                    self._say("Upload terminated. The previous list is kept.")
                    return
        else:
            return

        if not users:
            self._say("No valid participants found. The list was not loaded.")
            return
        self.users = users
        self.list_source = source
        self._say(f"Loaded {len(users)} participant(s) from the {source} list.")

    def show_groups(self) -> None:
        if not self.users:
            self._say("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say("Department groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            self._say(f"  {index}. {group}: {count} people")
        self._say(f"Total: {len(self.users)} people in {len(info)} groups.")

    # ----- prizes -----

    def prize_menu(self) -> None:
        while True:
            self._say(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._say(error)
                self._say("Preset prizes loaded.")
                self._show_prizes()
            elif choice == "3":
                self._add_custom_prize()
            elif choice == "4":
                self._configure_prize()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                self._say("Invalid option, please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured yet.")
            return
        self._say("Lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            self._say(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoidance groups: {groups} | Lottery person: {drawer}"
            )

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be an integer.")
            return
        groups_text = self._ask("Avoidance groups (comma-separated, optional): ")
        groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        drawer = self._ask("Associated lottery person (optional): ")
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer or None)
            self._say("Prize added.")
        except ValueError as exc:
            self._say(f"Could not add prize: {exc}")

    def _configure_prize(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured yet.")
            return
        self._show_prizes()
        index = self._parse_index(self._ask("Enter the prize number to configure: "), len(prizes))
        if index is None:
            return
        prize = prizes[index]
        current_groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        groups_text = self._ask(
            f"Avoidance groups (comma-separated; '-' to clear; empty to keep [{current_groups}]): "
        )
        if not groups_text:
            groups = list(prize.avoid_groups)
        elif groups_text == "-":
            groups = []
        else:
            groups = [group.strip() for group in groups_text.split(",") if group.strip()]

        current_drawer = prize.associated_drawer or "None"
        drawer_text = self._ask(
            f"Associated lottery person (empty to keep [{current_drawer}], '-' to clear): "
        )
        if not drawer_text:
            drawer = prize.associated_drawer
        elif drawer_text == "-":
            drawer = None
        else:
            drawer = drawer_text

        try:
            self.prize_manager.update_prize(index, groups, drawer)
            self._say("Prize configuration updated.")
        except ValueError as exc:
            self._say(f"Could not update prize: {exc}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured yet.")
            return
        self._show_prizes()
        text = self._ask(
            "Enter the new order as serial numbers separated by spaces (e.g. 3 1 2): "
        )
        try:
            order = [int(part) for part in text.split()]
        except ValueError:
            self._say("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Lottery sequence updated.")
            self._show_prizes()
        else:
            self._say("Invalid order: every serial number must appear exactly once.")

    def _parse_index(self, text: str, count: int) -> int | None:
        try:
            number = int(text)
        except ValueError:
            self._say("Invalid number.")
            return None
        if not 1 <= number <= count:
            self._say("Number out of range.")
            return None
        return number - 1

    # ----- lottery -----

    def start_lottery(self) -> None:
        if not self.users:
            self._say("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured. Please set up prizes first.")
            return
        if self.result_manager is not None and self.result_manager.count() > 0:
            confirm = self._ask("Previous results will be cleared. Continue? [y/N]: ").lower()
            if confirm != "y":
                return

        self.lottery_prizes = prizes
        self.lottery_manager = LotteryManager(self.users)
        self.result_manager = ResultManager()
        process = LotteryProcess(
            self.lottery_manager,
            self.result_manager,
            input_func=self._input,
            output_func=self._output,
        )
        process.run(prizes)
        self._show_summary(self.lottery_prizes)
        self._offer_export(self.lottery_prizes)

    def results_menu(self) -> None:
        if self.result_manager is None or self.result_manager.count() == 0:
            self._say("No results yet.")
            return
        self._show_summary(self.lottery_prizes)
        self._offer_export(self.lottery_prizes)

    def _show_summary(self, prizes) -> None:
        winners_map = self.result_manager.get_winners_by_prize(prizes)
        self._say("")
        self._say("=== Winner list (by prize level, then winning order) ===")
        for prize_name, winners in winners_map.items():
            self._say(f"{prize_name}:")
            if not winners:
                self._say("  (no winners)")
            for index, winner in enumerate(winners, start=1):
                self._say(f"  {index}. {winner.user.name} ({winner.user.department})")

    def _offer_export(self, prizes) -> None:
        answer = self._ask("Export the winner list to a txt (CSV format) file? [y/N]: ").lower()
        if answer == "y":
            _, message = self.result_manager.export_to_csv(prizes)
            self._say(message)


def main() -> int:
    cli = LotteryCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nProgram interrupted. Exiting.")
    return 0
