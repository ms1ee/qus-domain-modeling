"""Command-line interface controlling the whole lottery process."""
from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager, describe_rules
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


PRIZE_MENU = """
================ Prize Configuration ================
1. Load preset prizes
2. Add custom prize
3. Set avoidance groups for a prize
4. Set lottery person for a prize
5. View prizes and rules
6. Reorder prize sequence
7. View department groups
8. Start lottery
0. Exit
"""


def _ordinal(number: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery_manager: LotteryManager | None = None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _ask_index(self, prompt: str, count: int) -> int | None:
        """Ask for a 1-based number and return a 0-based index, or None if invalid."""
        text = self._ask(prompt)
        if not text.isdigit() or not 1 <= int(text) <= count:
            print("Invalid selection.")
            return None
        return int(text) - 1

    def _print_groups(self) -> None:
        if not self.users:
            print("No participants loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Valid department groups ({len(info)}):")
        for department, count in info.items():
            print(f"  - {department}: {count} people")

    # ------------------------------------------------------------ list loading
    def _setup_user_list(self) -> bool:
        while True:
            print("\n========== Participant List ==========")
            print("1. Load built-in team building list")
            print("2. Upload custom txt list (Name,Department Group per line)")
            print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
                for error in errors:
                    print(error)
                if not users:
                    print("Built-in list is empty.")
                    continue
                self.users = users
                print(f"Loaded {len(users)} participants from the built-in list.")
                self._print_groups()
                return True
            if choice == "2":
                if self._load_custom_list():
                    return True
            elif choice == "0":
                return False
            else:
                print("Invalid option.")

    def _load_custom_list(self) -> bool:
        path = self._ask("Enter the path of the custom txt file: ").strip('"')
        if not path:
            print("No path entered.")
            return False

        users, errors = self.list_manager.load_custom_list(path)
        for error in errors:
            print(error)
        if not users and errors:
            print("Upload failed: no readable data.")
            return False

        valid, duplicates = self.list_manager.validate_users(users)
        for dup in duplicates:
            print(f"Duplicate Name: '{dup.name}' ({dup.department}) appears more than once and is removed.")

        if errors or duplicates:
            print(f"Found {len(errors)} format error(s) and {len(duplicates)} duplicate(s).")
            while True:
                choice = self._ask(
                    "Type 'r' to remove invalid data and continue, or 't' to terminate the upload: "
                ).lower()
                if choice == "t":
                    print("Upload terminated.")
                    return False
                if choice == "r":
                    break
                print("Invalid choice.")

        if not valid:
            print("No valid participants found.")
            return False

        self.users = valid
        print(f"Loaded {len(valid)} participants from '{path}'.")
        self._print_groups()
        return True

    # ---------------------------------------------------------- prize config
    def _print_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(f"{index}. {prize.name} | Quantity: {prize.quantity}")
            print(f"   Rules: {describe_rules(prize)}")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Prize quantity: ")
        if not quantity_text.isdigit():
            print("Quantity must be a positive integer.")
            return
        groups_text = self._ask("Avoidance groups (comma separated, empty for none): ")
        groups = PrizeManager.parse_group_text(groups_text)
        drawer = self._choose_drawer()
        if drawer is False:
            return
        try:
            prize = self.prize_manager.add_prize(name, int(quantity_text), groups, drawer)
            print(f"Prize added: {prize.name}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def _choose_drawer(self) -> str | None | bool:
        """Return a valid drawer name, None for no drawer, or False on invalid input."""
        names = []
        for user in self.users:
            if user.name not in names:
                names.append(user.name)
        if names:
            print("Available lottery persons: " + ", ".join(names))
        text = self._ask("Associated lottery person (empty for none): ")
        if not text:
            return None
        if text not in names:
            print(f"'{text}' is not a participant in the loaded list.")
            return False
        return text

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes()
        index = self._ask_index("Select prize number: ", len(prizes))
        if index is None:
            return
        info = self.list_manager.get_group_info(self.users) if self.users else {}
        if info:
            print("Available groups: " + ", ".join(info.keys()))
        groups = PrizeManager.parse_group_text(
            self._ask("Avoidance groups (comma separated, empty to clear): ")
        )
        if self.prize_manager.set_avoid_groups(index, groups):
            print("Avoidance groups updated.")

    def _set_drawer(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes()
        index = self._ask_index("Select prize number: ", len(prizes))
        if index is None:
            return
        drawer = self._choose_drawer()
        if drawer is False:
            return
        if self.prize_manager.set_associated_drawer(index, drawer):
            print("Lottery person updated.")

    def _reorder(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (e.g. 3 1 2): "
        )
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Order must contain only numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
            self._print_prizes()
        else:
            print("Invalid order: each serial number must appear exactly once.")

    def _run_prize_menu(self) -> bool:
        """Run the prize configuration menu. Returns True if the lottery was run."""
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"Error: {error}")
                if not errors:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._set_drawer()
            elif choice == "5":
                self._print_prizes()
            elif choice == "6":
                self._reorder()
            elif choice == "7":
                self._print_groups()
            elif choice == "8":
                if not self.prize_manager.get_prizes():
                    print("Please configure at least one prize first.")
                    continue
                self._run_lottery()
                return True
            elif choice == "0":
                return False
            else:
                print("Invalid option.")

    # ------------------------------------------------------------- lottery
    def _run_lottery(self) -> None:
        self.lottery_manager = LotteryManager(self.users)
        prizes = self.prize_manager.get_prizes()
        print("\n========== Lottery Start ==========")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, prize)
        self._show_summary(prizes)
        self._offer_export(prizes)

    def _run_round(self, round_no: int, prize: Prize) -> None:
        assert self.lottery_manager is not None
        lm = self.lottery_manager
        print(f"\n----- Round {round_no}: {prize.name} | Quantity: {prize.quantity} -----")
        print(f"Rules: {describe_rules(prize)}")
        if lm.is_cheng_ru_protection_active(prize):
            print("Notice: Cheng Ru Group protection is active for this round.")

        round_winners: list[User] = []
        terminated = False
        draw_no = 1
        while draw_no <= prize.quantity:
            command = self._ask(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).lower()
            if command == "terminate":
                terminated = True
                break
            if command == "pause":
                print("Lottery paused.")
                if not self._wait_for_resume():
                    terminated = True
                    break
                print("Lottery resumed.")
                continue
            if command:
                print("Unknown command.")
                continue

            print(f"Currently drawing the {_ordinal(draw_no)} winner...")
            winner = lm.draw_one(prize)
            if winner is None:
                print("No eligible candidates remain for this prize. Round ends.")
                break
            self.result_manager.add_winner(winner, prize)
            round_winners.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}!")
            draw_no += 1

        lm.finish_round(prize, round_winners)
        if terminated:
            print("Current round terminated and skipped.")

        print(f"Round results for {prize.name}:")
        if not round_winners:
            print("  (no winners)")
        for index, winner in enumerate(round_winners, start=1):
            print(f"  {index}. {winner.name} ({winner.department})")

    def _wait_for_resume(self) -> bool:
        """Block until 'continue' (True) or 'terminate' (False)."""
        while True:
            command = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
            if command == "continue":
                return True
            if command == "terminate":
                return False
            print("Unknown command.")

    def _show_summary(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n========== Final Winner List ==========")
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.sequence}. Name: {winner.user.name} | "
                    f"Department: {winner.user.department} | Prize: {prize_name}"
                )

    def _offer_export(self, prizes: list[Prize]) -> None:
        choice = self._ask("\nExport the winner list to file? (y/n): ").lower()
        if choice in ("y", "yes"):
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)

    # ---------------------------------------------------------------- run
    def run(self) -> None:
        print("=====================================================")
        print("  Company Team Building Smart Lottery System")
        print("=====================================================")
        if not self._setup_user_list():
            print("Program exited.")
            return
        self._run_prize_menu()
        print("Thank you for using the lottery system. Goodbye!")


def main() -> int:
    """Program entry point. Returns a process exit code."""
    try:
        LotterySystemCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram interrupted. Exiting.")
        return 1
    return 0
