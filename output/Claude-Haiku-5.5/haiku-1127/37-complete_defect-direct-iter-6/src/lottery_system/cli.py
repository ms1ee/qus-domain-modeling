"""Command-line interface: list management, prize configuration, lottery control and results."""

from __future__ import annotations

import re
from typing import Callable

from lottery_system.models import Prize, User, normalize_text
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MENU_ITEMS: list[tuple[str, str]] = [
    ("1", "Load built-in default team building list"),
    ("2", "Upload custom txt list (Name,Department Group per line)"),
    ("3", "View department groups and member counts"),
    ("4", "Load preset prize library"),
    ("5", "Add custom prize"),
    ("6", "View prizes / adjust lottery order"),
    ("7", "Start lottery"),
    ("8", "Export winner list to txt (CSV format)"),
    ("0", "Exit"),
]


def _ordinal(number: int) -> str:
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line controller for the lottery system."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self._input = input_func
        self._output = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_done = False

    # ------------------------------------------------------------------ io
    def say(self, message: str = "") -> None:
        self._output(message)

    def ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    # ------------------------------------------------------------------ main loop
    def run(self) -> int:
        self.say("=== Company Team Building Smart Lottery System ===")
        handlers: dict[str, Callable[[], None]] = {
            "1": self.load_default_list,
            "2": self.load_custom_list,
            "3": self.show_groups,
            "4": self.load_default_prizes,
            "5": self.add_custom_prize,
            "6": self.manage_prize_order,
            "7": self.start_lottery,
            "8": self.export_results,
        }
        try:
            while True:
                self.say()
                self.say("Main Menu:")
                for key, label in MENU_ITEMS:
                    self.say(f"  {key}. {label}")
                choice = self.ask("Select an option: ")
                if choice == "0":
                    self.say("Goodbye!")
                    return 0
                handler = handlers.get(choice)
                if handler is None:
                    self.say("Invalid option, please try again.")
                    continue
                handler()
        except (EOFError, KeyboardInterrupt):
            self.say("\nLottery system closed.")
            return 0

    # ------------------------------------------------------------------ list management
    def load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._finalize_list(users, errors)

    def load_custom_list(self) -> None:
        path = self.ask("Enter the path of the txt file: ")
        users, errors = self.list_manager.load_custom_list(path)
        self._finalize_list(users, errors)

    def _finalize_list(self, users: list[User], errors: list[str]) -> None:
        if errors:
            self.say("Invalid entries detected:")
            for error in errors:
                self.say(f"  - {error}")
            if not self._confirm_discard("the invalid entries"):
                self.say("List upload terminated.")
                return

        valid_users, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self.say("Duplicate names detected (later occurrences):")
            for user in duplicates:
                self.say(f"  - {user.name} ({user.department})")
            if not self._confirm_discard("the duplicate entries"):
                self.say("List upload terminated.")
                return

        if not valid_users:
            self.say("No valid users found. The list was not loaded.")
            return

        self.users = valid_users
        self.result_manager = ResultManager()
        self.lottery = None
        self.lottery_done = False
        self.say(f"Loaded {len(valid_users)} valid users.")

    def _confirm_discard(self, label: str) -> bool:
        while True:
            answer = self.ask(
                f"Type 'remove' to discard {label} and continue, "
                "or 'terminate' to cancel the upload: "
            ).lower()
            if answer == "remove":
                return True
            if answer == "terminate":
                return False
            self.say("Please type 'remove' or 'terminate'.")

    def show_groups(self) -> None:
        if not self.users:
            self.say("No list loaded. Please load a participant list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        self.say("Department groups:")
        for group, count in info.items():
            self.say(f"  {group}: {count} people")
        self.say(f"Total: {len(self.users)} people in {len(info)} groups")

    # ------------------------------------------------------------------ prize configuration
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            self.say("Some preset prizes could not be loaded:")
            for error in errors:
                self.say(f"  - {error}")
        else:
            self.say("Preset prize library loaded.")
        self._show_prizes()

    def add_custom_prize(self) -> None:
        name = self.ask("Prize name: ")
        quantity_text = self.ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self.say("Quantity must be an integer.")
            return
        avoid_groups = self._choose_avoid_groups()
        drawer = self.ask("Associated lottery person (leave blank for none): ")
        try:
            prize = self.prize_manager.add_prize(
                name, quantity, avoid_groups, drawer or None
            )
        except ValueError as exc:
            self.say(f"Cannot add prize: {exc}")
            return
        self.say(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _choose_avoid_groups(self) -> list[str]:
        if not self.users:
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        self.say("Available department groups:")
        for index, group in enumerate(groups, start=1):
            self.say(f"  {index}. {group}")
        raw = self.ask(
            "Avoidance groups (numbers or names, comma-separated; blank for none): "
        )
        if not raw:
            return []
        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            match: str | None = None
            if token.isdigit():
                position = int(token) - 1
                if 0 <= position < len(groups):
                    match = groups[position]
            else:
                for group in groups:
                    if normalize_text(group) == normalize_text(token):
                        match = group
                        break
            if match is None:
                self.say(f"  Ignored unknown group: '{token}'")
            elif match not in selected:
                selected.append(match)
        return selected

    def manage_prize_order(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured yet.")
            return
        self._show_prizes()
        raw = self.ask(
            "Enter new order as serial numbers separated by commas "
            "(blank to keep current order): "
        )
        if not raw:
            return
        try:
            order = [int(token) for token in re.split(r"[\s,]+", raw) if token]
        except ValueError:
            self.say("Order must contain only serial numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.say("Prize order updated.")
            self._show_prizes()
        else:
            self.say("Invalid order: each serial number from 1 to N must appear exactly once.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured.")
            return
        self.say("Current lottery order:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self.say(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {avoid}"
            )

    # ------------------------------------------------------------------ lottery process
    def start_lottery(self) -> None:
        if not self.users:
            self.say("Please load a participant list first.")
            return
        if self.lottery_done:
            self.say(
                "A lottery has already been completed for the current list. "
                "Reload the list to start a new lottery."
            )
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.say("No prizes configured. Please load or add prizes first.")
            return

        self.lottery = LotteryManager(self.users)
        self.say("Lottery starting. Rounds in order:")
        for index, prize in enumerate(prizes, start=1):
            self.say(f"  Round {index}: {prize.name} (quantity {prize.quantity})")

        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)

        self.lottery_done = True
        self._show_final_results(prizes)

    def _control_prompt(self) -> str:
        """Wait for the operator's command. Returns 'draw' or 'terminate'."""
        while True:
            command = self.ask(
                "Press Enter to draw the next winner, 'pause' to pause, "
                "or 'terminate' to end this round: "
            ).lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "continue":
                self.say("The lottery is not paused.")
                continue
            if command == "pause":
                self.say("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self.ask("(paused) > ").lower()
                    if resume == "continue":
                        self.say("Lottery resumed.")
                        break
                    if resume == "terminate":
                        return "terminate"
                    self.say("Unknown command. Use 'continue' or 'terminate'.")
                continue
            self.say("Unknown command.")

    def _run_round(self, round_no: int, total_rounds: int, prize: Prize) -> None:
        assert self.lottery is not None
        self.say()
        self.say(f"=== Round {round_no}/{total_rounds}: {prize.name} | Quantity: {prize.quantity} ===")
        self.say(f"Rule: {self.lottery.describe_rule(prize)}")

        round_winners: list[User] = []
        for position in range(1, prize.quantity + 1):
            action = self._control_prompt()
            if action == "terminate":
                self.say("Round terminated early; remaining prizes of this round are skipped.")
                break
            self.say(f"Currently drawing the {_ordinal(position)} winner...")
            winner = self.lottery.draw_one(prize)
            if winner is None:
                self.say("No eligible candidates remain for this prize; round ends.")
                break
            round_winners.append(winner)
            self.result_manager.add_winner(winner, prize)
            self.say(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}"
            )

        self.lottery.finish_round(prize, round_winners)

        self.say(f"Round {round_no} results:")
        if not round_winners:
            self.say("  (no winners)")
        for number, winner in enumerate(round_winners, start=1):
            self.say(f"  {number}. {winner.name} | {winner.department}")

    def _show_final_results(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self.say()
        self.say("=== Final Winner List ===")
        for prize in prizes:
            winners = grouped.get(prize.name, [])
            self.say(f"{prize.name} ({len(winners)}/{prize.quantity} drawn)")
            if not winners:
                self.say("  (no winners)")
            for number, winner in enumerate(winners, start=1):
                self.say(f"  {number}. {winner.user.name} | {winner.user.department} | {prize.name}")

        answer = self.ask("Export the winner list to a txt file now? (y/n): ").lower()
        if answer in ("y", "yes"):
            self.export_results()

    # ------------------------------------------------------------------ results
    def export_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        _, message = self.result_manager.export_to_csv(prizes)
        self.say(message)


def main() -> int:
    """Program entry point."""
    return LotterySystemCLI().run()
