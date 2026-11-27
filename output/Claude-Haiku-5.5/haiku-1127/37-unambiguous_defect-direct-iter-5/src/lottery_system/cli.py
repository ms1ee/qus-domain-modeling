"""Command-line interface for the company team building lottery."""

from __future__ import annotations

import re

from lottery_system.default_data import DRAWER_OPTIONS, LI_BIN, MA_JIAQI
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

BANNER = """
==============================================
   Company Team Building Smart Lottery System
==============================================
"""


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self, input_func=input, output_func=print) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _set_users(self, users) -> None:
        self.users = list(users)
        self.lottery = None
        self._print(f"Participant list loaded: {len(self.users)} valid people.")

    def _report_problems(self, errors, duplicates) -> None:
        if errors:
            self._print(f"\n{len(errors)} format error(s) found:")
            for error in errors:
                self._print(f"  - {error}")
        if duplicates:
            self._print(f"\n{len(duplicates)} duplicate name(s) found:")
            for user in duplicates:
                self._print(f"  - Duplicate: '{user.name}' ({user.department})")

    def _groups(self) -> list[str]:
        return sorted(self.list_manager.get_group_info(self.users).keys())

    def _count_winners(self, prize_name: str) -> int:
        return sum(
            1 for winner in self.result_manager.get_all_winners()
            if winner.prize_name == prize_name
        )

    # --------------------------------------------------------------- main menu
    def run(self) -> None:
        self._print(BANNER)
        while True:
            self._print("\n=== Main Menu ===")
            self._print("1. Participant list management")
            self._print("2. Prize configuration")
            self._print("3. Start lottery")
            self._print("4. View results and export")
            self._print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._list_menu()
            elif choice == "2":
                self._prize_menu()
            elif choice == "3":
                self._start_lottery()
            elif choice == "4":
                self._results_menu()
            elif choice == "0":
                self._print("Goodbye!")
                return
            else:
                self._print("Invalid option, please try again.")

    # ------------------------------------------------------------ list module
    def _list_menu(self) -> None:
        while True:
            self._print(f"\n=== Participant List (currently loaded: {len(self.users)}) ===")
            self._print("1. Load built-in default list")
            self._print("2. Upload custom txt list")
            self._print("3. View department groups and headcount")
            self._print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._load_custom_list()
            elif choice == "3":
                self._show_groups()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        valid, duplicates = self.list_manager.validate_users(users)
        self._report_problems(errors, duplicates)
        self._set_users(valid)

    def _load_custom_list(self) -> None:
        self._print("Custom txt format: one person per line, 'name,department'.")
        path = self._ask("Enter the path of the txt file: ")
        if not path:
            self._print("No path entered; upload cancelled.")
            return

        users, errors = self.list_manager.load_custom_list(path)
        if not users:
            for error in errors:
                self._print(f"  - {error}")
            self._print("No valid data could be read; the current list is unchanged.")
            return

        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self._set_users(valid)
            return

        self._report_problems(errors, duplicates)
        while True:
            choice = self._ask(
                "Enter 'r' to remove invalid/duplicate entries and continue, "
                "or 't' to terminate the upload: "
            ).lower()
            if choice == "r":
                self._set_users(valid)
                return
            if choice == "t":
                self._print("Upload terminated; the current list is unchanged.")
                return
            self._print("Please enter 'r' or 't'.")

    def _show_groups(self) -> None:
        if not self.users:
            self._print("No participants loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("\nDepartment groups:")
        for department in sorted(info):
            self._print(f"  {department}: {info[department]} people")
        self._print(f"Total: {len(self.users)} people")

    # ----------------------------------------------------------- prize module
    def _prize_menu(self) -> None:
        while True:
            self._print("\n=== Prize Configuration ===")
            self._print("1. Load preset prize library")
            self._print("2. Add custom prize")
            self._print("3. View prizes")
            self._print("4. Reorder lottery rounds")
            self._print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._print(f"  - {error}")
                self._print("Preset prizes loaded.")
            elif choice == "2":
                self._add_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def _ask_quantity(self) -> int:
        while True:
            raw = self._ask("Prize quantity: ")
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            self._print("Please enter a positive whole number.")

    def _choose_groups(self) -> list[str]:
        groups = self._groups()
        if not groups:
            return []
        self._print("Available department groups:")
        for index, group in enumerate(groups, start=1):
            self._print(f"  {index}. {group}")
        raw = self._ask("Avoidance group numbers (comma-separated, Enter for none): ")
        selected: list[str] = []
        for token in re.split(r"[\s,]+", raw):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
                if name not in selected:
                    selected.append(name)
            else:
                self._print(f"Ignored invalid group number: {token}")
        return selected

    def _choose_drawer(self) -> str | None:
        self._print("Associated lottery person:")
        for index, drawer in enumerate(DRAWER_OPTIONS, start=1):
            self._print(f"  {index}. {drawer}")
        raw = self._ask("Enter a number, a custom name, or Enter for none: ")
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(DRAWER_OPTIONS):
            return DRAWER_OPTIONS[int(raw) - 1]
        return raw

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_quantity()
        groups = self._choose_groups()
        drawer = self._choose_drawer()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._print(f"Could not add prize: {exc}")
            return
        self._print(f"Prize '{name.strip()}' added.")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("\nCurrent lottery order:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            self._print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {avoid} | Lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._view_prizes()
        raw = self._ask("Enter new order as serial numbers (e.g. '2 1 3'): ")
        try:
            order = [int(token) for token in re.split(r"[\s,]+", raw) if token]
        except ValueError:
            self._print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Lottery order updated.")
        else:
            self._print("Invalid order: every serial number must appear exactly once.")

    # -------------------------------------------------------- lottery control
    def _describe_rule(self, prize) -> str:
        drawer = prize.associated_drawer or "None"
        rules: list[str] = []
        if (prize.associated_drawer or "").strip().casefold() == LI_BIN.casefold():
            rules.append("relaxed rules (only previous winners excluded)")
        else:
            rules.append("previous winners excluded")
            if prize.avoid_groups:
                rules.append("avoid groups: " + ", ".join(prize.avoid_groups))
        if (prize.associated_drawer or "").strip().casefold() == MA_JIAQI.casefold():
            rules.append("Cheng Ru group protection may apply")
        return f"Lottery person: {drawer}; Rules: " + "; ".join(rules)

    def _wait_until_resumed(self) -> bool:
        """Block while paused. Returns False if the round was terminated."""
        self._print("Lottery paused.")
        while True:
            command = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
            if command == "continue":
                self._print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._print("Please enter 'continue' or 'terminate'.")

    def _run_round(self, index: int, total: int, prize, remaining: int) -> None:
        self._print(f"\n=== Round {index}/{total}: {prize.name} ===")
        self._print(f"Quantity to draw: {remaining} | Rule: {self._describe_rule(prize)}")

        round_winners = []
        while len(round_winners) < remaining:
            if not self.lottery._get_eligible_pool(prize):
                self._print("No eligible candidates remain; this round ends.")
                break

            command = self._ask(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).lower()
            if command == "terminate":
                self._print("Round terminated and skipped.")
                break
            if command == "pause":
                if not self._wait_until_resumed():
                    self._print("Round terminated and skipped.")
                    break
            elif command:
                self._print("Unknown command.")
                continue

            position = len(round_winners) + 1
            self._print(f"Currently drawing the {_ordinal(position)} winner...")
            winner = self.lottery.draw_one(prize)
            if winner is None:
                self._print("No eligible candidates remain; this round ends.")
                break
            round_winners.append(winner)
            user = winner.user
            self._print(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}!"
            )

        self._print(f"Round finished: {len(round_winners)} winner(s) drawn for {prize.name}.")

    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured. Please configure prizes first.")
            return

        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)

        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            remaining = prize.quantity - self._count_winners(prize.name)
            if remaining <= 0:
                self._print(f"\nRound {index}/{total}: {prize.name} already completed; skipped.")
                continue
            self._run_round(index, total, prize, remaining)

        self._print("\nAll lottery rounds have been processed.")
        self._show_results(prizes)

    # ----------------------------------------------------------- results
    def _show_results(self, prizes) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            self._print("No winners yet.")
            return
        self._print("\n=== Winner List (by prize level) ===")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self._print(f"\n[{prize_name}]")
            for position, winner in enumerate(winners, start=1):
                self._print(
                    f"  {position}. {winner.user.name} ({winner.user.department})"
                )

    def _results_menu(self) -> None:
        prizes = self.prize_manager.get_prizes()
        self._show_results(prizes)
        if not self.result_manager.get_all_winners():
            return
        choice = self._ask("Export the winner list to a txt file? (y/n): ").lower()
        if choice == "y":
            _, message = self.result_manager.export_to_csv(prizes)
            self._print(message)


def main() -> None:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExited.")


if __name__ == "__main__":
    main()
