"""Command-line interface controlling configuration, lottery process and results."""

from __future__ import annotations

from lottery_system.constants import LOTTERY_PERSONS
from lottery_system.models import Prize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

MAIN_MENU = """
==================== Team Building Lottery ====================
1. Load participant list
2. View department groups
3. Configure prizes
4. Start lottery
5. View winner list
6. Export results to txt
0. Exit
==============================================================
"""

PRIZE_MENU = """
--- Prize configuration ---
1. Load preset prizes
2. Add custom prize
3. Reorder prizes
4. View prizes
0. Back
"""


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer (1st, 2nd, 11th...)."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list = []
        self.lottery: LotteryManager | None = None
        self.completed_prize_names: set[str] = set()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _confirm(self, prompt: str) -> bool:
        return self._ask(prompt).lower() in ("y", "yes")

    def _available_groups(self) -> list[str]:
        if not self.users:
            return []
        return list(self.list_manager.get_group_info(self.users).keys())

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("Welcome to the Smart Lottery System.")
        while True:
            print(MAIN_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._menu_load_list()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._menu_prizes()
            elif choice == "4":
                self._run_lottery()
            elif choice == "5":
                self._show_results()
            elif choice == "6":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------ list management
    def _menu_load_list(self) -> None:
        if self.result_manager.get_winners():
            print("Cannot reload the participant list after the lottery has started.")
            return
        print("1. Built-in default list\n2. Custom txt file\n0. Cancel")
        choice = self._ask("Select a loading mode: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        if errors:
            print(f"Found {len(errors)} invalid line(s):")
            for error in errors:
                print(f"  {error}")
            if not self._confirm("Remove invalid data and continue? (y/n): "):
                print("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  Duplicate: {user.name} ({user.department})")
            if not self._confirm("Remove duplicates and keep first occurrences? (y/n): "):
                print("Upload terminated.")
                return

        if not valid:
            print("No valid participants found. The list was not loaded.")
            return

        self.users = valid
        self.lottery = None
        print(f"Loaded {len(valid)} participant(s).")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Valid groups: {len(info)}")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department}: {count} member(s)")

    # ------------------------------------------------------- prize management
    def _menu_prizes(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(error)
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._reorder_prizes()
            elif choice == "4":
                self._view_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        raw_quantity = self._ask("Quantity: ")
        if not raw_quantity.isdigit() or int(raw_quantity) <= 0:
            print("Quantity must be a positive integer.")
            return
        drawer = self._select_drawer()
        avoid_groups = self._select_groups()
        try:
            self.prize_manager.add_prize(name, int(raw_quantity), avoid_groups, drawer)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print("Prize added.")

    def _select_drawer(self) -> str | None:
        print("Lottery persons:")
        for index, person in enumerate(LOTTERY_PERSONS, start=1):
            print(f"  {index}. {person}")
        raw = self._ask("Select lottery person number (0 for none): ")
        if raw in ("", "0"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(LOTTERY_PERSONS):
            return LOTTERY_PERSONS[int(raw) - 1]
        print("Invalid lottery person number; no lottery person assigned.")
        return None

    def _select_groups(self) -> list[str]:
        groups = self._available_groups()
        if not groups:
            print("No participant list loaded; avoidance groups cannot be selected.")
            return []
        print("Department groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        raw = self._ask("Enter group numbers to avoid (comma-separated, blank for none): ")
        selected: list[str] = []
        for token in raw.replace(" ", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                group = groups[int(token) - 1]
                if group not in selected:
                    selected.append(group)
            else:
                print(f"Ignored invalid group number: {token}")
        return selected

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes(prizes)
        raw = self._ask("Enter new order as serial numbers (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self._print_prizes(self.prize_manager.get_prizes())
        else:
            print("Invalid order: each serial number must appear exactly once.")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes(prizes)

    @staticmethod
    def _print_prizes(prizes: list[Prize]) -> None:
        for prize in prizes:
            drawer = prize.associated_drawer or "None"
            groups = ", ".join(prize.avoid_groups) or "None"
            print(
                f"{prize.sequence_number}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {groups}"
            )

    # ------------------------------------------------------- lottery process
    def _run_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        pending = [prize for prize in prizes if prize.name not in self.completed_prize_names]
        if not pending:
            print("All prizes have already been drawn.")
            return
        total = len(pending)
        print(f"Lottery starts: {total} round(s) in the configured order.")
        for round_no, prize in enumerate(pending, start=1):
            self._run_round(round_no, total, prize)
        print("\nAll lottery rounds finished. Use option 5 to view the complete winner list.")

    def _run_round(self, round_no: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {round_no}/{total}: {prize.name} | Quantity: {prize.quantity} ===")
        for rule in self.lottery.describe_rules(prize):
            print(f"  - {rule}")

        round_winners: list[Winner] = []
        for position in range(1, prize.quantity + 1):
            if not self._control_gate():
                print("Round terminated; remaining winners of this prize are skipped.")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_winner(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            round_winners.append(self.result_manager.add_winner(user, prize))
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.completed_prize_names.add(prize.name)
        print(f"\n--- Round {round_no}/{total} results: {prize.name} ---")
        if round_winners:
            for index, winner in enumerate(round_winners, start=1):
                print(f"  {index}. {winner.user.name} ({winner.user.department})")
        else:
            print("  No winners in this round.")

    def _control_gate(self) -> bool:
        """Wait for the operator before a draw. Returns False if the round is terminated."""
        while True:
            command = self._ask("[Enter] draw next | 'pause' | 'terminate' > ").lower()
            if command == "":
                return True
            if command == "terminate":
                return False
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                return self._paused_loop()
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _paused_loop(self) -> bool:
        while True:
            command = self._ask("paused > ").lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Lottery is paused. Type 'continue' or 'terminate'.")

    # ---------------------------------------------------------------- results
    def _show_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        ranked = self.result_manager.get_ranked_winners(prizes)
        if not ranked:
            print("No winners yet.")
            return
        print("\n==================== Winner List ====================")
        current: str | None = None
        index = 0
        for winner in ranked:
            if winner.prize_name != current:
                current = winner.prize_name
                index = 0
                print(f"\n[{current}]")
            index += 1
            print(f"  {index}. {winner.user.name} ({winner.user.department})")
        print("=====================================================")

    def _export_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        _, message = self.result_manager.export_to_csv(prizes)
        print(message)


def main() -> None:
    """Application entry point."""
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
