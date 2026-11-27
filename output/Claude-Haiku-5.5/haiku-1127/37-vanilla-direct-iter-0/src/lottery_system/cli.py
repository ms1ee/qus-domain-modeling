"""Command-line interaction for the lottery process."""

from __future__ import annotations

from typing import Callable

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, describe_rules
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(number: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 3rd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller of the whole lottery process."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
    ) -> None:
        self._input_func = input_func
        self._output = output
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self._groups: list[str] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ helpers
    def _say(self, text: str = "") -> None:
        self._output(text)

    def _ask(self, prompt: str) -> str:
        return self._input_func(prompt).strip()

    @staticmethod
    def _parse_numbers(text: str) -> list[int] | None:
        """Parse numbers separated by commas and/or spaces. None if invalid."""
        numbers: list[int] = []
        for token in text.replace(" ", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if not token.isdigit():
                return None
            numbers.append(int(token))
        return numbers

    # --------------------------------------------------------------- main flow
    def run(self) -> int:
        try:
            self._say("=" * 60)
            self._say("  Company Team Building - Smart Lottery System")
            self._say("=" * 60)
            self._setup_list()
            self._setup_prizes()
            self._run_lottery()
            self._show_summary()
            self._export_prompt()
        except (EOFError, KeyboardInterrupt):
            self._say("\nExiting the lottery system.")
        return 0

    # ------------------------------------------------------------ list setup
    def _setup_list(self) -> None:
        while True:
            self._say("\n=== Step 1: Load participant list ===")
            self._say("1) Built-in default team building list")
            self._say("2) Upload custom txt list (each line: Name,Department Group)")
            choice = self._ask("Select an option: ")
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self._ask("Enter txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
            else:
                self._say("Invalid option.")
                continue
            valid = self._verify_list(users, errors)
            if valid is None:
                continue
            self.users = valid
            break
        self._show_groups()

    def _verify_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self._say(f"List verified: {len(valid)} participants loaded.")
            return valid

        if errors:
            self._say("Invalid data found:")
            for error in errors:
                self._say(f"  - {error}")
        if duplicates:
            self._say("Duplicate names found (only the first occurrence is kept):")
            for user in duplicates:
                self._say(f"  - {user.name} ({user.department})")
        if not valid:
            self._say("No valid participants available.")
            return None

        choice = self._ask(
            "Enter 'r' to remove invalid/duplicate data and continue, "
            "or 't' to terminate the upload: "
        ).lower()
        if choice == "r":
            self._say(f"Continuing with {len(valid)} valid participants.")
            return valid
        self._say("Upload terminated.")
        return None

    def _show_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        self._groups = list(info.keys())
        self._say("\nValid department groups:")
        for number, (department, count) in enumerate(info.items(), start=1):
            self._say(f"  {number}. {department}: {count} people")

    # ----------------------------------------------------------- prize setup
    def _setup_prizes(self) -> None:
        while True:
            self._say("\n=== Step 2: Prize configuration ===")
            self._say("1) Load preset prize library")
            self._say("2) Add custom prize")
            self._say("3) Show prize list")
            self._say("4) Set lottery round order")
            self._say("5) Show department groups")
            self._say("6) Finish configuration and start lottery")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._say(f"  - {error}")
                else:
                    self._say("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._show_groups()
            elif choice == "6":
                if not self.prize_manager.get_prizes():
                    self._say("Please add at least one prize first.")
                    continue
                return
            else:
                self._say("Invalid option.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            self._say("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            self._say("Quantity must be a positive integer.")
            return

        self._say("Department groups (avoid groups are excluded from this prize):")
        for number, department in enumerate(self._groups, start=1):
            self._say(f"  {number}. {department}")
        group_text = self._ask(
            "Avoid groups (serial numbers separated by commas, blank for none): "
        )
        numbers = self._parse_numbers(group_text)
        if numbers is None or any(n < 1 or n > len(self._groups) for n in numbers):
            self._say("Invalid avoid group selection.")
            return
        avoid_groups = [self._groups[n - 1] for n in numbers]

        drawer = self._ask("Associated lottery person (blank for none): ")
        try:
            self.prize_manager.add_prize(
                name, int(quantity_text), avoid_groups, drawer or None
            )
        except ValueError as exc:
            self._say(f"Failed to add prize: {exc}")
            return
        self._say("Prize added.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._say("\nCurrent round order:")
        for number, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            self._say(
                f"  {number}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {avoid} | Lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        self._show_prizes()
        if not self.prize_manager.get_prizes():
            return
        text = self._ask(
            "Enter new round order as serial numbers separated by spaces "
            "(blank to keep current order): "
        )
        if not text:
            return
        numbers = self._parse_numbers(text)
        if numbers is None or not self.prize_manager.reorder_prizes(numbers):
            self._say("Invalid order. Each serial number must appear exactly once.")
            return
        self._say("Round order updated.")
        self._show_prizes()

    # --------------------------------------------------------------- lottery
    def _run_lottery(self) -> None:
        self.lottery = LotteryManager(self.users)
        prizes = self.prize_manager.get_prizes()
        self._say("\n=== Step 3: Lottery ===")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)
        self._say("\nAll lottery rounds completed.")

    def _run_round(self, index: int, total: int, prize) -> None:
        assert self.lottery is not None
        self._say(f"\n--- Round {index}/{total}: {prize.name} ---")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rules: {describe_rules(prize)}")
        choice = self._ask(
            "Press Enter to start this round, or type 'terminate' to skip it: "
        ).lower()
        if choice == "terminate":
            self._say("Round skipped.")
            return

        round_winners = []
        for position in range(1, prize.quantity + 1):
            self._say(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                self._say("No eligible candidates remain; ending this round early.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            self._say(
                f"Congratulations {user.name} ({user.department}) "
                f"for winning {prize.name}!"
            )
            if position == prize.quantity:
                break
            if self._round_control() == "terminate":
                self._say("Round terminated by operator; skipping the rest.")
                break

        self.lottery.finish_round(prize)

        self._say(f"Round results for {prize.name}:")
        if not round_winners:
            self._say("  (no winners)")
        for number, winner in enumerate(round_winners, start=1):
            self._say(
                f"  {ordinal(number)}. {winner.user.name} "
                f"({winner.user.department})"
            )

    def _round_control(self) -> str:
        """Between draws: Enter=next, 'pause' suspends, 'terminate' ends the round."""
        while True:
            command = self._ask(
                "[Enter] next draw | 'pause' | 'terminate': "
            ).lower()
            if command in ("", "continue"):
                return "next"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                self._say("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("> ").lower()
                    if resume == "continue":
                        self._say("Lottery resumed.")
                        return "next"
                    if resume == "terminate":
                        return "terminate"
                    self._say("Please type 'continue' or 'terminate'.")
            self._say("Unknown command.")

    # --------------------------------------------------------------- results
    def _show_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._say("\n=== Final Winner List ===")
        for prize_name, winners in grouped.items():
            self._say(f"\n{prize_name}")
            if not winners:
                self._say("  (no winners)")
            for number, winner in enumerate(winners, start=1):
                self._say(
                    f"  {number}. {winner.user.name} ({winner.user.department}) "
                    f"- {winner.win_time}"
                )

    def _export_prompt(self) -> None:
        choice = self._ask("\nExport the winner list to a txt file (CSV format)? (y/n): ").lower()
        if choice not in ("y", "yes"):
            return
        _, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self._say(message)


def main() -> int:
    """Program entry point."""
    return LotteryCLI().run()
