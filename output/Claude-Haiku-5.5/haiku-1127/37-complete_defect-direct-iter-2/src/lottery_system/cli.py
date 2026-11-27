"""Command-line interaction for the team building smart lottery system."""

from __future__ import annotations

from lottery_system.models import LOTTERY_DRAWERS, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MAIN_MENU = """
========== Team Building Smart Lottery ==========
1. Load participant list
2. View department groups
3. Prize configuration
4. Start lottery
5. View results
6. Export results
0. Exit
"""

PRIZE_MENU = """
---------- Prize Configuration ----------
1. Load default prize library
2. Add custom prize
3. View prizes (current order)
4. Reorder prizes
0. Back
"""


def ordinal(n: int) -> str:
    """Return the English ordinal form of n (1st, 2nd, 3rd, 11th, ...)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    """Interactive console application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.result_manager = ResultManager()
        self.last_prizes: list[Prize] = []
        self.has_results = False

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        while True:
            print(MAIN_MENU)
            choice = self._input("Select an option: ")
            try:
                if choice == "1":
                    self._load_list_menu()
                elif choice == "2":
                    self._show_groups()
                elif choice == "3":
                    self._prize_menu()
                elif choice == "4":
                    self._start_lottery()
                elif choice == "5":
                    self._view_results()
                elif choice == "6":
                    self._export_results()
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Invalid option, please try again.")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

    @staticmethod
    def _input(prompt: str) -> str:
        return input(prompt).strip()

    # ------------------------------------------------------------------ list management
    def _load_list_menu(self) -> None:
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (each line: Name,Department Group)")
        print("0. Cancel")
        choice = self._input("Select source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._input("Enter the txt file path: ").strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return
        self._verify_and_apply(users, errors)

    def _verify_and_apply(self, users: list[User], errors: list[str]) -> None:
        valid, duplicates = self.list_manager.validate_users(users)

        if not errors and not duplicates:
            self.users = valid
            print(f"List loaded successfully: {len(valid)} participants.")
            return

        print("\nList verification found problems:")
        for error in errors:
            print(f"  - {error}")
        for dup in duplicates:
            print(f"  - Duplicate Name: '{dup.name}' ({dup.department}) appears more than once")
        print(f"Valid participants: {len(valid)}")
        print("1. Remove invalid/duplicate data and continue with valid entries")
        print("2. Terminate upload (keep previous list)")

        choice = self._input("Select an option: ")
        if choice == "1":
            if not valid:
                print("No valid participants remain. Upload terminated, previous list kept.")
                return
            self.users = valid
            print(f"List loaded with invalid/duplicate data removed: {len(valid)} participants.")
        else:
            print("Upload terminated. Previous list kept.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self.users)} people")

    # ------------------------------------------------------------------ prize configuration
    def _prize_menu(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._input("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(error)
                print("Default prize library loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._input("Prize name: ")
        if not name:
            print("Prize name must not be empty.")
            return
        try:
            quantity = int(self._input("Quantity: "))
        except ValueError:
            print("Quantity must be an integer.")
            return

        if self.users:
            print("Known department groups: " + ", ".join(self.list_manager.get_group_info(self.users)))
        groups_text = self._input("Avoidance groups (comma separated, blank for none): ")
        avoid_groups = [g.strip() for g in groups_text.split(",") if g.strip()]

        print("Associated lottery person:")
        print("0. None")
        for index, drawer in enumerate(LOTTERY_DRAWERS, start=1):
            print(f"{index}. {drawer}")
        drawer_choice = self._input("Select lottery person: ")
        drawer: str | None = None
        if drawer_choice.isdigit() and 1 <= int(drawer_choice) <= len(LOTTERY_DRAWERS):
            drawer = LOTTERY_DRAWERS[int(drawer_choice) - 1]

        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nCurrent lottery order:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                  f"Avoid groups: {groups} | Lottery person: {drawer}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._input("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            print("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: must contain every serial number exactly once.")

    # ------------------------------------------------------------------ lottery
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        self.last_prizes = prizes
        self.has_results = False

        print("\nLottery started.")
        print("At each draw prompt: press Enter to draw the next winner, "
              "type 'pause' to pause, or 'terminate' to end the current round.")

        for index, prize in enumerate(prizes, start=1):
            self._run_round(lottery, index, prize)

        self.has_results = True
        print("\nAll lottery rounds completed.")
        self._show_results(prizes)

    def _run_round(self, lottery: LotteryManager, index: int, prize: Prize) -> None:
        print(f"\n----- Round {index}: {prize.name} -----")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        round_winners: list[User] = []
        drawn = 0
        while drawn < prize.quantity:
            if lottery.count_eligible(prize) == 0:
                print("No eligible candidates remain for this round. Round ends.")
                break

            command = self._input("[Enter] draw next / 'pause' / 'terminate': ").lower()
            if command == "pause":
                if not self._handle_pause():
                    print("Current round terminated and skipped.")
                    break
                continue
            if command == "terminate":
                print("Current round terminated and skipped.")
                break
            if command == "continue":
                print("Lottery is not paused.")
                continue
            if command != "":
                print("Unknown command. Press Enter to draw, or type 'pause' / 'terminate'.")
                continue

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = lottery.draw_next(prize)
            if user is None:
                print("No eligible candidates remain for this round. Round ends.")
                break
            drawn += 1
            self.result_manager.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        lottery.complete_round(prize, round_winners)

        print(f"\nRound {index} results ({prize.name}):")
        if not round_winners:
            print("  No winners in this round.")
        for position, user in enumerate(round_winners, start=1):
            print(f"  {position}. {user.name} ({user.department})")

    def _handle_pause(self) -> bool:
        """Block until 'continue' (returns True) or 'terminate' (returns False)."""
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._input("> ").lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Please type 'continue' or 'terminate'.")

    # ------------------------------------------------------------------ results
    def _show_results(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n===== Complete Winner List =====")
        print(f"{'No.':<5}{'Name':<16}{'Department':<30}Prize")
        number = 0
        for prize in prizes:
            for winner in grouped.get(prize.name, []):
                number += 1
                print(f"{number:<5}{winner.user.name:<16}{winner.user.department:<30}{winner.prize_name}")
        if number == 0:
            print("No winners.")
        print(f"Total winners: {number}")

    def _view_results(self) -> None:
        if not self.has_results:
            print("No lottery results yet. Run the lottery first.")
            return
        self._show_results(self.last_prizes)

    def _export_results(self) -> None:
        if not self.has_results:
            print("No lottery results to export. Run the lottery first.")
            return
        success, message = self.result_manager.export_to_csv(self.last_prizes)
        print(message)


def main() -> None:
    """Entry point for the lottery command-line application."""
    LotterySystemCLI().run()


if __name__ == "__main__":
    main()
