"""Command-line interface: list management, prize configuration, lottery control and results."""

from __future__ import annotations

from typing import Callable

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

MAIN_MENU = """
==================== Main Menu ====================
 1. Load built-in default participant list
 2. Upload custom txt participant list
 3. View department groups and member counts
 4. Prize configuration
 5. Start lottery
 6. View winner summary
 7. Export winner list (txt)
 0. Exit
"""

PRIZE_MENU = """
------------------- Prize Configuration -------------------
 1. View prizes
 2. Load preset prizes
 3. Add custom prize
 4. Set avoidance groups / lottery person for a prize
 5. Reorder lottery sequence
 0. Back to main menu
"""


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self, input_func: Callable[[str], str] = input) -> None:
        self._input = input_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    @staticmethod
    def _print(message: str = "") -> None:
        print(message)

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        self._print("Welcome to the Team Building Smart Lottery System")
        while True:
            self._print(MAIN_MENU)
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._upload_custom_list()
            elif choice == "3":
                self._show_groups()
            elif choice == "4":
                self._prize_menu()
            elif choice == "5":
                self._start_lottery()
            elif choice == "6":
                self._print_summary()
            elif choice == "7":
                self._export()
            elif choice == "0":
                self._print("Goodbye!")
                return
            else:
                self._print("Invalid option, please try again.")

    # ------------------------------------------------------------ list module
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        if self._review_and_apply(users, errors):
            self._print(f"Built-in list loaded: {len(self.users)} participants.")

    def _upload_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file: ").strip().strip('"').strip("'")
        if not path:
            self._print("No path entered. Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        if self._review_and_apply(users, errors):
            self._print(f"Custom list loaded: {len(self.users)} participants.")

    def _review_and_apply(self, users: list[User], errors: list[str]) -> bool:
        """Validate loaded users; ask the operator how to handle any issues."""
        valid, duplicates = self.list_manager.validate_users(users)

        if not errors and not duplicates:
            self.users = valid
            return True

        self._print("Validation found the following issues:")
        for error in errors:
            self._print(f"  - {error}")
        for dup in duplicates:
            self._print(
                f"  - Duplicate Name: '{dup.name}' ({dup.department}) appears more than once; "
                f"first occurrence is kept"
            )
        self._print(f"Valid entries available: {len(valid)}")

        while True:
            choice = self._ask(
                "Enter R to remove invalid data and keep valid entries, "
                "or T to terminate the upload: "
            ).strip().lower()
            if choice == "r":
                self.users = valid
                self._print(f"Invalid data removed. Keeping {len(valid)} valid entries.")
                return True
            if choice == "t":
                self._print("Upload terminated. The previous participant list is unchanged.")
                return False
            self._print("Please enter R or T.")

    def _show_groups(self) -> None:
        if not self.users:
            self._print("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("Department groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            self._print(f"  {index}. {group}: {count} people")
        self._print(f"Total: {len(self.users)} participants in {len(info)} groups.")

    # ----------------------------------------------------------- prize module
    def _prize_menu(self) -> None:
        while True:
            self._print(PRIZE_MENU)
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._print(f"  - {error}")
                else:
                    self._print("Preset prizes loaded.")
            elif choice == "3":
                self._add_custom_prize()
            elif choice == "4":
                self._edit_prize_rules()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured yet.")
            return
        self._print("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            self._print(f"  {index}. {self._format_prize(prize)}")

    @staticmethod
    def _format_prize(prize: Prize) -> str:
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "-"
        drawer = prize.associated_drawer or "-"
        return f"{prize.name} | quantity: {prize.quantity} | lottery person: {drawer} | avoid: {groups}"

    def _select_groups(self) -> list[str]:
        known: list[str] = []
        if self.users:
            known = list(self.list_manager.get_group_info(self.users).keys())
            self._print("Available groups:")
            for index, group in enumerate(known, start=1):
                self._print(f"  {index}. {group}")

        raw = self._ask(
            "Enter avoidance groups (numbers or names, comma-separated; blank for none): "
        ).strip()
        if not raw:
            return []

        selected: list[str] = []
        for token in (part.strip() for part in raw.split(",")):
            if not token:
                continue
            if token.isdigit() and known and 1 <= int(token) <= len(known):
                name = known[int(token) - 1]
            else:
                name = token
            if name not in selected:
                selected.append(name)
        return selected

    def _ask_drawer(self) -> str | None:
        raw = self._ask("Associated lottery person (blank for none): ").strip()
        return raw or None

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
            if quantity < 1:
                raise ValueError
        except ValueError:
            self._print("Quantity must be a positive integer.")
            return

        groups = self._select_groups()
        drawer = self._ask_drawer()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer, is_custom=True)
        except ValueError as exc:
            self._print(str(exc))
            return
        self._print(f"Prize added: {self._format_prize(prize)}")

    def _edit_prize_rules(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured yet.")
            return
        self._show_prizes()
        raw = self._ask("Enter the prize serial number to edit: ").strip()
        if not raw.isdigit() or not (1 <= int(raw) <= len(prizes)):
            self._print("Invalid serial number.")
            return
        prize = prizes[int(raw) - 1]
        groups = self._select_groups()
        drawer = self._ask_drawer()
        self.prize_manager.update_rules(prize.name, groups, drawer)
        self._print(f"Updated: {self._format_prize(prize)}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            self._print("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        raw = self._ask("Enter the new round order as serial numbers (e.g. 2 1 3): ")
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            self._print("Invalid input: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Lottery sequence updated.")
            self._show_prizes()
        else:
            self._print("Invalid order: every serial number must appear exactly once.")

    # -------------------------------------------------------- lottery control
    def _start_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure at least one prize first.")
            return

        if self.result_manager.winners:
            confirm = self._ask("Previous results will be cleared. Continue? (y/n): ").strip().lower()
            if confirm != "y":
                self._print("Lottery cancelled.")
                return
            self.result_manager.clear()

        lottery = LotteryManager(self.users)
        total_rounds = len(prizes)
        self._print(f"\nLottery starts: {total_rounds} round(s).")
        self._print("Commands during a round: Enter = draw next, 'pause', 'continue', 'terminate'.")

        for round_no, prize in enumerate(prizes, start=1):
            round_winners = self._run_round(lottery, prize, round_no, total_rounds)
            self._print(f"\n--- Round {round_no} results ({prize.name}) ---")
            if round_winners:
                for winner in round_winners:
                    self._print(
                        f"  #{winner.winning_order} {winner.user.name} ({winner.user.department})"
                    )
            else:
                self._print("  No winners in this round.")

        self._print("\nAll rounds completed.")
        self._print_summary()

    def _run_round(
        self,
        lottery: LotteryManager,
        prize: Prize,
        round_no: int,
        total_rounds: int,
    ) -> list[Winner]:
        self._print(
            f"\n=== Round {round_no}/{total_rounds}: {prize.name} | "
            f"Quantity: {prize.quantity} ==="
        )
        self._print(f"Rule: {lottery.describe_rules(prize)}")

        round_winners: list[Winner] = []
        drawn = 0
        paused = False

        while drawn < prize.quantity:
            if paused:
                prompt = "[PAUSED] Type 'continue' to resume or 'terminate' to end this round: "
            else:
                prompt = (
                    f"Press Enter to draw winner #{drawn + 1}, "
                    f"or type 'pause' / 'terminate': "
                )
            command = self._ask(prompt).strip().lower()

            if paused:
                if command == "continue":
                    paused = False
                    self._print("Lottery resumed.")
                elif command == "terminate":
                    self._print("Round terminated manually. Skipping remaining winners of this prize.")
                    break
                else:
                    self._print("Lottery is paused. Type 'continue' or 'terminate'.")
                continue

            if command == "pause":
                paused = True
                self._print("Lottery paused.")
                continue
            if command == "terminate":
                self._print("Round terminated manually. Skipping remaining winners of this prize.")
                break
            if command != "":
                self._print("Unknown command. Press Enter to draw, or type 'pause' / 'terminate'.")
                continue

            self._print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = lottery.draw(prize)
            if user is None:
                self._print("No eligible candidates remain for this prize. Round ends early.")
                break

            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            drawn += 1
            self._print(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}!"
            )

        return round_winners

    # --------------------------------------------------------- results module
    def _print_summary(self) -> None:
        if not self.result_manager.winners:
            self._print("No winners recorded yet.")
            return
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._print("\n==================== Winner List ====================")
        for prize_name, winners in grouped.items():
            self._print(f"\n[{prize_name}]")
            if not winners:
                self._print("  (no winners drawn)")
                continue
            for winner in winners:
                self._print(
                    f"  #{winner.winning_order} {winner.user.name} "
                    f"({winner.user.department}) - {prize_name}"
                )

    def _export(self) -> None:
        if not self.result_manager.winners:
            self._print("No winners to export. Run the lottery first.")
            return
        _, message = self._export_result()
        self._print(message)

    def _export_result(self) -> tuple[bool, str]:
        return self.result_manager.export_to_csv(self.prize_manager.get_prizes())


def main() -> None:
    """Start the interactive lottery system."""
    cli = LotteryCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")


if __name__ == "__main__":
    main()
