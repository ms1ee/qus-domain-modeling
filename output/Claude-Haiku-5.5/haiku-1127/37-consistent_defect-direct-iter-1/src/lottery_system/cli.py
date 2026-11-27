"""Command-line interface for the lottery system."""

from __future__ import annotations

import random
from typing import Callable

from lottery_system.models import Prize, User, normalize_text
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import DRAWER_OPTIONS, LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(number: int) -> str:
    """Return an English ordinal string such as 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
        rng: random.Random | None = None,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self._rng = rng
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []

    # ------------------------------------------------------------ utilities
    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            raw = self._ask(prompt)
            try:
                value = int(raw)
                if value > 0:
                    return value
            except ValueError:
                pass
            self._print("Please enter a positive whole number.")

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    # ------------------------------------------------------------ entry
    def run(self) -> int:
        self._print("=" * 60)
        self._print("  Company Team Building Smart Lottery System")
        self._print("=" * 60)
        try:
            if not self._load_list_stage():
                self._print("Goodbye.")
                return 0
            self._main_menu()
        except (EOFError, KeyboardInterrupt):
            self._print("\nSession ended.")
        return 0

    # ------------------------------------------------------- list loading
    def _load_list_stage(self) -> bool:
        while True:
            self._print("\n--- Load Participant List ---")
            self._print("1. Use built-in default team building list")
            self._print("2. Upload custom txt list (format: Name,Department Group)")
            self._print("0. Exit")
            choice = self._ask("Select: ")

            if choice == "0":
                return False
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self._ask("Enter path of txt file: ")
                users, errors = self.list_manager.load_custom_list(path)
            else:
                self._print("Invalid option.")
                continue

            accepted = self._verify_list(users, errors)
            if accepted is None:
                self._print("Upload terminated.")
                continue
            if not accepted:
                self._print("No valid participants were loaded. Please try again.")
                continue

            self.users = accepted
            self._print(f"Loaded {len(self.users)} valid participants.")
            self._show_groups()
            return True

    def _verify_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Verify the loaded list. Returns valid users, or None if upload terminated."""
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            return valid

        self._print("List verification found problems:")
        for error in errors:
            self._print(f"  - {error}")
        for dup in duplicates:
            self._print(f"  - Duplicate name: {dup.name} ({dup.department})")

        while True:
            choice = self._ask("[r] remove invalid data and continue / [q] terminate upload: ").lower()
            if choice == "r":
                return valid
            if choice == "q":
                return None
            self._print("Please enter 'r' or 'q'.")

    def _show_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        self._print("\nValid department groups:")
        if not info:
            self._print("  (none)")
            return
        for group, count in info.items():
            self._print(f"  {group}: {count} people")

    # ------------------------------------------------------------ main menu
    def _main_menu(self) -> None:
        while True:
            self._print("\n=== Main Menu ===")
            self._print("1. View participant list and group information")
            self._print("2. Prize configuration")
            self._print("3. Start lottery")
            self._print("0. Exit")
            choice = self._ask("Select: ")
            if choice == "1":
                self._show_groups()
            elif choice == "2":
                self._prize_menu()
            elif choice == "3":
                self._start_lottery()
            elif choice == "0":
                self._print("Goodbye.")
                return
            else:
                self._print("Invalid option.")

    # ---------------------------------------------------------- prize config
    def _prize_menu(self) -> None:
        while True:
            self._print("\n--- Prize Configuration ---")
            self._print("1. Load preset prize library")
            self._print("2. Add custom prize")
            self._print("3. Edit prize avoidance groups / lottery person")
            self._print("4. View prizes")
            self._print("5. Reorder lottery sequence")
            self._print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._print(f"  - {error}")
                else:
                    self._print("Preset prizes loaded.")
            elif choice == "2":
                self._add_prize_flow()
            elif choice == "3":
                self._edit_prize_flow()
            elif choice == "4":
                self._show_prizes()
            elif choice == "5":
                self._reorder_flow()
            elif choice == "0":
                return
            else:
                self._print("Invalid option.")

    def _add_prize_flow(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            self._print("Prize name must not be empty.")
            return
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self._choose_drawer()
        groups = self._choose_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
            self._print(f"Prize added: {prize.name} (quantity {prize.quantity}).")
        except ValueError as exc:
            self._print(f"Failed to add prize: {exc}")

    def _edit_prize_flow(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._show_prizes()
        raw = self._ask("Select prize number to edit (blank to cancel): ")
        if not raw:
            return
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            self._print("Invalid prize number.")
            return
        index = int(raw) - 1
        self._print("1. Change avoidance groups")
        self._print("2. Change associated lottery person")
        choice = self._ask("Select: ")
        if choice == "1":
            groups = self._choose_groups()
            self.prize_manager.set_avoid_groups(index, groups)
            self._print("Avoidance groups updated.")
        elif choice == "2":
            drawer = self._choose_drawer()
            self.prize_manager.set_associated_drawer(index, drawer)
            self._print("Associated lottery person updated.")
        else:
            self._print("Invalid option.")

    def _choose_drawer(self) -> str | None:
        self._print("Associated lottery person (optional):")
        for index, drawer in enumerate(DRAWER_OPTIONS, start=1):
            self._print(f"  {index}. {drawer}")
        self._print("  0. None (anyone)")
        raw = self._ask("Select number, or type a custom name (blank = none): ")
        if not raw or raw == "0":
            return None
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(DRAWER_OPTIONS):
                return DRAWER_OPTIONS[index - 1]
            self._print("Invalid number; no lottery person assigned.")
            return None
        return raw

    def _choose_groups(self) -> list[str]:
        groups = self._group_names()
        if not groups:
            self._print("No participant list loaded; no avoidance groups can be set.")
            return []
        self._print("Available department groups:")
        for index, group in enumerate(groups, start=1):
            self._print(f"  {index}. {group}")
        raw = self._ask("Avoidance groups (numbers or names, comma-separated; blank = none): ")
        return self._resolve_groups(raw, groups)

    def _resolve_groups(self, raw: str, groups: list[str]) -> list[str]:
        selected: list[str] = []
        for token in raw.split(","):
            text = token.strip()
            if not text:
                continue
            if text.isdigit() and 1 <= int(text) <= len(groups):
                match = groups[int(text) - 1]
            else:
                match = next(
                    (g for g in groups if normalize_text(g) == normalize_text(text)), None
                )
                if match is None:
                    self._print(f"Warning: unknown group '{text}' ignored.")
                    continue
            if match not in selected:
                selected.append(match)
        return selected

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "Anyone"
            avoid = ", ".join(prize.avoid_groups) or "None"
            self._print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {avoid}"
            )

    def _reorder_flow(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._show_prizes()
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(item) for item in raw.split()]
        except ValueError:
            self._print("Invalid input: use whole numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Lottery sequence updated.")
            self._show_prizes()
        else:
            self._print("Invalid order: each serial number must appear exactly once.")

    # ------------------------------------------------------------ lottery
    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return

        self.result_manager = ResultManager()
        lottery = LotteryManager(self.users, rng=self._rng)
        total = len(prizes)
        self._print("\n##### Lottery started #####")
        for round_no, prize in enumerate(prizes, start=1):
            self._print(f"\n##### Round {round_no}/{total} #####")
            winners = self._run_round(lottery, prize)
            lottery.finish_round(prize, winners)
            self._show_round_results(winners)

        self._show_summary(prizes)
        self._export_prompt(prizes)

    def _run_round(self, lottery: LotteryManager, prize: Prize) -> list[User]:
        winners: list[User] = []
        self._print(
            f"Prize: {prize.name} | Quantity: {prize.quantity} | "
            f"Lottery person: {prize.associated_drawer or 'Anyone'}"
        )
        self._print(f"Rules: {lottery.rule_description(prize)}")

        for position in range(1, prize.quantity + 1):
            prompt = (
                f"Press Enter to draw the {ordinal(position)} winner "
                f"(or 'pause' / 'terminate'): "
            )
            if not self._control_gate(prompt):
                self._print("Round terminated.")
                break

            self._print(f"Currently drawing the {ordinal(position)} winner...")
            winner = lottery.draw_one(prize)
            if winner is None:
                self._print("No eligible participants remain for this prize. Round ends.")
                break

            self.result_manager.add_winner(winner, prize)
            winners.append(winner)
            self._print(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}"
            )
        return winners

    def _control_gate(self, prompt: str) -> bool:
        """Handle lottery control commands. Returns True to draw, False to end the round."""
        while True:
            command = self._ask(prompt).lower()
            if command in ("", "continue"):
                return True
            if command == "terminate":
                return False
            if command == "pause":
                return self._wait_while_paused()
            self._print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _wait_while_paused(self) -> bool:
        self._print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._ask("[paused] > ").lower()
            if command == "continue":
                self._print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._print("Type 'continue' to resume or 'terminate' to end this round.")

    def _show_round_results(self, winners: list[User]) -> None:
        if not winners:
            self._print("No winners were drawn in this round.")
            return
        self._print("Round results (winning order):")
        for index, user in enumerate(winners, start=1):
            self._print(f"  {index}. {user.name} ({user.department})")

    def _show_summary(self, prizes: list[Prize]) -> None:
        self._print("\n##### Final Winner List #####")
        grouped = self.result_manager.get_winners_by_prize(prizes)
        for prize_name, winners in grouped.items():
            self._print(f"[{prize_name}]")
            if not winners:
                self._print("  (no winners)")
                continue
            for index, winner in enumerate(winners, start=1):
                self._print(
                    f"  {index}. {winner.user.name} | {winner.user.department} | {winner.prize_name}"
                )

    def _export_prompt(self, prizes: list[Prize]) -> None:
        answer = self._ask("Export winner list to file? [y/n]: ").lower()
        if answer in ("y", "yes"):
            _, message = self.result_manager.export_to_csv(prizes)
            self._print(message)


def main() -> int:
    """Application entry point."""
    return LotterySystemCLI().run()
