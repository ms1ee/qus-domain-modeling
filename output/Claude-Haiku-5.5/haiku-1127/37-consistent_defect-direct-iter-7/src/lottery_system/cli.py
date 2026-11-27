"""Command-line interface for the team building smart lottery."""

from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LOTTERY_PERSONS, LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

MENU = """
========== Team Building Smart Lottery ==========
1. Load participant list
2. View department groups
3. Configure prizes
4. Start lottery
5. View / export results
0. Exit
"""


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    def __init__(self, input_func=input, output_func=print) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.lottery: LotteryManager | None = None

    # ----- basic helpers -----

    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def run(self) -> None:
        try:
            while True:
                self._print(MENU)
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self._menu_load_list()
                elif choice == "2":
                    self._menu_view_groups()
                elif choice == "3":
                    self._menu_prizes()
                elif choice == "4":
                    self._start_lottery()
                elif choice == "5":
                    self._menu_results()
                elif choice == "0":
                    self._print("Goodbye!")
                    return
                else:
                    self._print("Invalid option, please try again.")
        except (EOFError, KeyboardInterrupt):
            self._print("\nExiting.")

    # ----- participant list -----

    def _menu_load_list(self) -> None:
        self._print("1. Built-in team building list")
        self._print("2. Custom txt list (each line: Name,Department)")
        self._print("0. Back")
        choice = self._ask("Select: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        for error in errors:
            self._print(error)

        valid, duplicates = self.list_manager.validate_users(users)
        for dup in duplicates:
            self._print(f"Duplicate Name: '{dup.name}' ({dup.department}) - later entry ignored.")

        if errors or duplicates:
            self._print(
                f"Detected {len(errors)} format error(s) and {len(duplicates)} duplicate(s)."
            )
            self._print("Enter 'r' to remove invalid data and continue, or 'q' to terminate upload.")
            while True:
                action = self._ask("Choice (r/q): ").lower()
                if action == "r":
                    break
                if action == "q":
                    self._print("Upload terminated; participant list unchanged.")
                    return
                self._print("Please enter 'r' or 'q'.")

        if not valid:
            self._print("No valid participants found.")
            return

        self.users = valid
        self.lottery = None
        self._print(f"Loaded {len(valid)} participant(s).")

    def _groups(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    def _menu_view_groups(self) -> None:
        if not self.users:
            self._print("Please load the participant list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("\nDepartment groups:")
        for index, (dept, count) in enumerate(info.items(), start=1):
            self._print(f"  {index}. {dept}: {count} people")
        self._print(f"Total: {len(self.users)} people")

    # ----- prizes -----

    def _menu_prizes(self) -> None:
        while True:
            self._print("\n--- Prize configuration ---")
            self._print("1. Load preset prizes")
            self._print("2. Add custom prize")
            self._print("3. Reorder prizes")
            self._print("4. View prizes")
            self._print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._print(error)
                if not errors:
                    self._print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._reorder_prizes()
            elif choice == "4":
                self._show_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {groups} | lottery person: {drawer}"
            )

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            self._print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._print("Quantity must be an integer.")
            return
        groups = self._choose_avoid_groups()
        drawer = self._choose_drawer()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._print(f"Failed to add prize: {exc}")
            return
        self._print(f"Prize '{name}' added.")

    def _choose_avoid_groups(self) -> list[str]:
        groups = self._groups()
        if groups:
            self._print("Department groups:")
            for index, dept in enumerate(groups, start=1):
                self._print(f"  {index}. {dept}")
        text = self._ask(
            "Avoidance groups (numbers or names, comma-separated; blank for none): "
        )
        result: list[str] = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                value = groups[int(token) - 1]
            else:
                value = token
            if value not in result:
                result.append(value)
        return result

    def _choose_drawer(self) -> str | None:
        self._print("Lottery persons:")
        for index, person in enumerate(LOTTERY_PERSONS, start=1):
            self._print(f"  {index}. {person}")
        text = self._ask("Associated lottery person (number or name; blank for none): ")
        if not text:
            return None
        if text.isdigit() and 1 <= int(text) <= len(LOTTERY_PERSONS):
            return LOTTERY_PERSONS[int(text) - 1]
        return text

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            self._print("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (e.g. 2 1 3): "
        )
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            self._print("Serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize order updated.")
            self._show_prizes()
        else:
            self._print("Invalid order: every serial number must appear exactly once.")

    # ----- lottery process -----

    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return
        if self.lottery and self.lottery.result_manager.winners:
            answer = self._ask("Previous results will be cleared. Continue? (y/n): ").lower()
            if answer != "y":
                return

        self.lottery = LotteryManager(self.users)
        total = len(prizes)
        self._print("\nCommands before each draw: [Enter]/continue = draw, pause = pause, terminate = end this round.")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)

        self._print("\n========== Lottery finished ==========")
        self._print_results(self.lottery.result_manager, prizes)

    def _run_round(self, index: int, total: int, prize) -> None:
        assert self.lottery is not None
        self._print(
            f"\n----- Round {index}/{total}: {prize.name} | Quantity: {prize.quantity} -----"
        )
        self._print(f"Rule: {self.lottery.describe_rules(prize)}")

        self.lottery.start_round(prize)
        drawn = 0
        while drawn < prize.quantity:
            if not self._wait_for_command():
                self._print("Round terminated by user.")
                break
            self._print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            winner = self.lottery.draw_next(prize)
            if winner is None:
                self._print("No eligible participants remain for this prize.")
                break
            drawn += 1
            user = winner.user
            self._print(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}!"
            )
        self.lottery.end_round(prize)

        round_winners = [
            w for w in self.lottery.result_manager.winners if w.prize_name == prize.name
        ]
        self._print(
            f"Round {index} finished: {len(round_winners)}/{prize.quantity} winner(s)."
        )

    def _wait_for_command(self) -> bool:
        """Handle control commands before a draw. Returns False to terminate the round."""
        command = self._ask("[Enter] draw | pause | terminate > ").lower()
        while True:
            if command == "pause":
                self._print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    command = self._ask("[paused] continue / terminate > ").lower()
                    if command == "continue":
                        self._print("Lottery resumed.")
                        return True
                    if command == "terminate":
                        return False
                    self._print("While paused, only 'continue' or 'terminate' is accepted.")
            if command == "terminate":
                return False
            if command in ("", "continue"):
                return True
            self._print("Unknown command. Use Enter, 'pause' or 'terminate'.")
            command = self._ask("[Enter] draw | pause | terminate > ").lower()

    # ----- results -----

    def _print_results(self, result_manager: ResultManager, prizes) -> None:
        ranked: list[Winner] = result_manager.get_ranked_winners(prizes)
        if not ranked:
            self._print("No winners yet.")
            return
        self._print(f"{'Name':<16}{'Department':<30}{'Prize Name':<40}{'Time'}")
        for winner in ranked:
            self._print(
                f"{winner.user.name:<16}{winner.user.department:<30}"
                f"{winner.prize_name:<40}{winner.timestamp}"
            )

    def _menu_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        while True:
            self._print("\n--- Results ---")
            self._print("1. View winner list")
            self._print("2. Export winner list (txt/CSV)")
            self._print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                if self.lottery is None:
                    self._print("No lottery has been run yet.")
                else:
                    self._print_results(self.lottery.result_manager, prizes)
            elif choice == "2":
                if self.lottery is None:
                    self._print("No lottery has been run yet.")
                    continue
                _, message = self.lottery.result_manager.export_to_csv(prizes)
                self._print(message)
            elif choice == "0":
                return
            else:
                self._print("Invalid option.")


def main() -> None:
    LotterySystemCLI().run()
