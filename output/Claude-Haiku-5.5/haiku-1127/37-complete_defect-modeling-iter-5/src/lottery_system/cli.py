"""Command-line interface: menus, lottery process control and result display."""

from __future__ import annotations

from typing import Callable, Optional

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MAIN_MENU = """
========== Team Building Smart Lottery ==========
1. Load participant list
2. View department groups
3. Configure prizes
4. Reorder prize sequence
5. Start lottery
6. View results / export results
0. Exit"""

PRIZE_MENU = """
---------- Prize Configuration ----------
1. Load preset prizes
2. Add custom prize
3. Show prizes
0. Back"""


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _parse_ints(text: str) -> Optional[list[int]]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    try:
        return [int(part) for part in parts]
    except ValueError:
        return None


class LotteryCLI:
    """Interactive command-line controller for the lottery system."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.results = ResultManager()
        self.users: list[User] = []
        self.list_loaded = False
        self.lottery: Optional[LotteryManager] = None

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str = "") -> str:
        return self._input(prompt).strip()

    def _out(self, text: str = "") -> None:
        self._print(text)

    # ---------------------------------------------------------------- main loop
    def run(self) -> None:
        self._out("Welcome to the Team Building Smart Lottery System.")
        try:
            while True:
                self._out(MAIN_MENU)
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self.load_list()
                elif choice == "2":
                    self.show_groups()
                elif choice == "3":
                    self.configure_prizes()
                elif choice == "4":
                    self.reorder_prizes()
                elif choice == "5":
                    self.start_lottery()
                elif choice == "6":
                    self.show_results_and_export()
                elif choice == "0":
                    self._out("Goodbye!")
                    return
                else:
                    self._out("Invalid option, please try again.")
        except (EOFError, KeyboardInterrupt):
            self._out("\nExiting. Goodbye!")

    # ------------------------------------------------------------ list module
    def load_list(self) -> None:
        self._out("1. Built-in default team building list")
        self._out("2. Custom txt list (each line: Name,Department Group)")
        mode = self._ask("Choose load mode: ")
        if mode == "1":
            users, errors = self.list_manager.load_default_list()
        elif mode == "2":
            path = self._ask("Enter the txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            self._out("Invalid choice.")
            return

        for error in errors:
            self._out(error)

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._out("Duplicate names detected (later entries are duplicates):")
            for user in duplicates:
                self._out(f"  - {user.name} ({user.department})")

        if errors or duplicates:
            self._out("Invalid data detected. Options:")
            self._out("  [R] Remove invalid data and continue")
            self._out("  [T] Terminate upload")
            while True:
                action = self._ask("Choose R or T: ").lower()
                if action == "r":
                    break
                if action == "t":
                    self._out("Upload terminated. Participant list unchanged.")
                    return
                self._out("Please enter R or T.")

        if not valid:
            self._out("No valid participants loaded.")
            return

        self.users = valid
        self.list_loaded = True
        self.lottery = None
        self._out(f"Loaded {len(valid)} valid participant(s).")

    def show_groups(self) -> None:
        if not self.list_loaded:
            self._out("No participant list loaded yet.")
            return
        groups = self.list_manager.get_group_info(self.users)
        self._out("Department groups:")
        for index, (group, count) in enumerate(groups.items(), start=1):
            self._out(f"  {index}. {group}: {count} member(s)")

    # ----------------------------------------------------------- prize module
    def configure_prizes(self) -> None:
        while True:
            self._out(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._out(f"Skipped: {error}")
                else:
                    self._out("Preset prizes loaded.")
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.show_prizes()
            elif choice == "0":
                return
            else:
                self._out("Invalid option.")

    def add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Prize quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._out("Quantity must be an integer.")
            return

        avoid_groups = self._select_avoid_groups()
        if avoid_groups is None:
            return
        drawer = self._ask("Associated lottery person (blank for none): ")

        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid_groups, drawer or None)
        except ValueError as exc:
            self._out(f"Cannot add prize: {exc}")
            return
        self._out(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _select_avoid_groups(self) -> Optional[list[str]]:
        if not self.list_loaded:
            self._out("No participant list loaded; avoidance groups cannot be selected.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        self._out("Select avoidance groups (blank for none):")
        for index, group in enumerate(groups, start=1):
            self._out(f"  {index}. {group}")
        while True:
            text = self._ask("Enter group numbers separated by commas: ")
            if not text:
                return []
            numbers = _parse_ints(text)
            if numbers is None or any(n < 1 or n > len(groups) for n in numbers):
                self._out("Invalid selection, please try again.")
                continue
            return [groups[n - 1] for n in dict.fromkeys(numbers)]

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("No prizes configured.")
            return
        self._out("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._out(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {avoid} | lottery person: {drawer}"
            )

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("No prizes configured.")
            return
        self.show_prizes()
        text = self._ask("Enter new order as serial numbers separated by commas (e.g. 2,1,3): ")
        order = _parse_ints(text)
        if order is None or not self.prize_manager.reorder_prizes(order):
            self._out("Invalid order. The sequence was not changed.")
            return
        self._out("Prize sequence updated.")
        self.show_prizes()

    # ------------------------------------------------------- lottery process
    def start_lottery(self) -> None:
        if not self.list_loaded:
            self._out("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("Please configure at least one prize first.")
            return

        self.lottery = LotteryManager(self.users)
        self.results = ResultManager()
        self._out("Lottery started. Commands: pause / continue / terminate")

        for number, prize in enumerate(prizes, start=1):
            self._run_round(number, prize)

        self._out("\n========== Lottery Finished ==========")
        self._show_summary(prizes)

    def _run_round(self, number: int, prize: Prize) -> None:
        lottery = self.lottery
        assert lottery is not None
        self._out(f"\n--- Round {number}: {prize.name} ---")
        self._out(f"Quantity: {prize.quantity}")
        self._out(f"Rule: {lottery.describe_rule(prize)}")

        pool_size = len(lottery.eligible_pool(prize))
        if pool_size == 0:
            self._out("No eligible participants for this prize. Round skipped.")
            lottery.finish_round(prize, [])
            return
        if pool_size < prize.quantity:
            self._out(
                f"Note: only {pool_size} eligible participant(s); fewer winners will be drawn."
            )

        round_winners: list[User] = []
        for position in range(1, prize.quantity + 1):
            if self._control() == "terminate":
                self._out("Round terminated by operator; remaining winners skipped.")
                break
            self._out(f"Currently drawing the {_ordinal(position)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                self._out("No eligible participants left. Round ends early.")
                break
            round_winners.append(user)
            self.results.add_winner(user, prize)
            self._out(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        lottery.finish_round(prize, round_winners)

        self._out(f"Round {number} results (winning order):")
        if not round_winners:
            self._out("  (no winners)")
        for index, user in enumerate(round_winners, start=1):
            self._out(f"  {index}. {user.name} ({user.department})")

    def _control(self) -> str:
        """Process operator commands before each draw. Returns 'next' or 'terminate'."""
        while True:
            command = self._ask("[Enter]=draw next | pause | terminate: ").lower()
            if command in ("", "continue"):
                return "next"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                self._out("Lottery PAUSED. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    command = self._ask("(paused) > ").lower()
                    if command == "continue":
                        self._out("Lottery resumed.")
                        return "next"
                    if command == "terminate":
                        return "terminate"
                    self._out("Type 'continue' or 'terminate'.")
            self._out("Unknown command. Use Enter, pause, or terminate.")

    # ------------------------------------------------------- results module
    def _show_summary(self, prizes: list[Prize]) -> None:
        grouped = self.results.get_winners_by_prize(prizes)
        total = 0
        self._out("Complete winner list:")
        self._out(f"  {'Name':<16}| {'Department':<24}| Prize")
        for prize in prizes:
            for winner in grouped.get(prize.name, []):
                total += 1
                self._out(
                    f"  {winner.user.name:<16}| {winner.user.department:<24}| {winner.prize_name}"
                )
        if total == 0:
            self._out("  (no winners)")
        self._out(f"Total winners: {total}")

    def show_results_and_export(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.results.get_all_winners():
            self._out("No lottery results yet.")
            return
        self._show_summary(prizes)
        if self._ask("Export results to txt/CSV file? (y/n): ").lower() == "y":
            _, message = self.results.export_to_csv(prizes)
            self._out(message)


def main() -> None:
    """Start the interactive lottery system."""
    LotteryCLI().run()
