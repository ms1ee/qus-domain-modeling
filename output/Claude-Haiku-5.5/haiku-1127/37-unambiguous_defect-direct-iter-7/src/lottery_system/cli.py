"""Command-line interface for the team building smart lottery system."""

from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner


def ordinal(number: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 11th."""
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _ask(prompt: str) -> str:
    return input(prompt).strip()


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.results: ResultManager | None = None
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            self._print_main_menu()
            choice = _ask("Select an option: ")
            if choice == "1":
                self._load_list_flow()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "5":
                self._show_summary()
            elif choice == "6":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    @staticmethod
    def _print_main_menu() -> None:
        print("\nMain Menu:")
        print("  1. Load participant list")
        print("  2. View department groups")
        print("  3. Prize configuration")
        print("  4. Start lottery")
        print("  5. View winner summary")
        print("  6. Export results")
        print("  0. Exit")

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------
    def _load_list_flow(self) -> None:
        print("\nList source:")
        print("  1. Built-in default team building list")
        print("  2. Custom txt file (one 'Name,Department' per line)")
        print("  0. Cancel")
        choice = _ask("Select source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = _ask("Enter txt file path: ").strip('"')
            if not path:
                print("Cancelled.")
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Cancelled.")
            return

        accepted = self._verify_users(users, errors)
        if accepted is None:
            print("Upload terminated. Current participant list unchanged.")
            return
        self.users = accepted
        print(f"Loaded {len(self.users)} participants.")
        self._show_groups()

    def _verify_users(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Verify list content. Returns accepted users, or None if terminated."""
        if errors:
            print(f"\n{len(errors)} format error(s) found:")
            for error in errors:
                print(f"  {error}")
            answer = _ask("Remove invalid data and continue? (r = remove and continue / t = terminate): ").lower()
            if answer != "r":
                return None

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"\n{len(duplicates)} duplicate name(s) found:")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            answer = _ask("Remove duplicates and continue? (r = remove and continue / t = terminate): ").lower()
            if answer != "r":
                return None

        if not valid:
            print("No valid participants found.")
            return None
        return valid

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nDepartment groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")

    # ------------------------------------------------------------------
    # Prize configuration
    # ------------------------------------------------------------------
    def _prize_menu(self) -> None:
        while True:
            print("\nPrize Configuration:")
            print("  1. Load preset prize library")
            print("  2. Add custom prize")
            print("  3. View prizes")
            print("  4. Reorder lottery rounds")
            print("  0. Back")
            choice = _ask("Select option: ")
            if choice == "1":
                self._load_default_prizes()
            elif choice == "2":
                self._add_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(f"  {error}")
        else:
            print("Preset prize library loaded.")

    def _ask_avoid_groups(self) -> list[str]:
        group_names = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        if group_names:
            print("Available groups:")
            for index, name in enumerate(group_names, start=1):
                print(f"  {index}. {name}")
        raw = _ask("Avoidance groups (comma-separated names or numbers, blank for none): ")
        groups: list[str] = []
        for token in [item.strip() for item in raw.split(",") if item.strip()]:
            if token.isdigit() and group_names and 1 <= int(token) <= len(group_names):
                groups.append(group_names[int(token) - 1])
            else:
                groups.append(token)
        return groups

    def _add_prize(self) -> None:
        name = _ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity_text = _ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be a positive integer.")
            return
        groups = self._ask_avoid_groups()
        drawer = _ask("Associated lottery person (leave blank for none): ")
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer or None)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                  f"avoid: {avoid} | drawer: {drawer}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        raw = _ask("Enter new order as serial numbers separated by spaces: ")
        try:
            order = [int(token) for token in raw.split()]
        except ValueError:
            print("Invalid input: please enter serial numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._view_prizes()
        else:
            print("Invalid order: every prize position must appear exactly once.")

    # ------------------------------------------------------------------
    # Lottery process
    # ------------------------------------------------------------------
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        self.results = ResultManager()
        self.lottery = LotteryManager(self.users)
        print("\nLottery started!")
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
        print("\nAll lottery rounds completed.")
        self._print_summary(prizes)

    def _run_round(self, index: int, total: int, prize: Prize) -> list[User]:
        assert self.lottery is not None and self.results is not None
        print("\n" + "-" * 60)
        print(f"Round {index}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {self.lottery.describe_rules(prize)}")
        pool_size = len(self.lottery.get_eligible_pool(prize))
        print(f"Eligible candidates: {pool_size}")
        print("-" * 60)

        if pool_size == 0:
            print("No eligible candidates, this round is skipped.")
            self.lottery.end_round(prize)
            return []

        self.lottery.start_round(prize)
        drawn = 0
        while drawn < prize.quantity:
            action = self._prompt_action()
            if action == "terminate":
                print("Round terminated by operator.")
                break
            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = self.lottery.draw_next(prize)
            if user is None:
                print("No more eligible candidates, round ends early.")
                break
            drawn += 1
            self.results.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        winners = self.lottery.end_round(prize)
        print(f"\nRound {index} results ({prize.name}):")
        if not winners:
            print("  (no winners)")
        for position, user in enumerate(winners, start=1):
            print(f"  {position}. {user.name} ({user.department})")
        return winners

    @staticmethod
    def _prompt_action() -> str:
        """Wait for operator input. Returns 'draw' or 'terminate'."""
        while True:
            command = _ask("[Enter] draw next | 'pause' | 'terminate': ").lower()
            if command in ("", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    paused_command = _ask("paused> ").lower()
                    if paused_command == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if paused_command == "terminate":
                        return "terminate"
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def _print_summary(self, prizes: list[Prize]) -> None:
        if self.results is None:
            print("No lottery results yet.")
            return
        grouped = self.results.get_winners_by_prize(prizes)
        print("\n" + "=" * 60)
        print("  Winner Summary (by prize level, high to low)")
        print("=" * 60)
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                self._print_winner_line(winner)

    @staticmethod
    def _print_winner_line(winner: Winner) -> None:
        print(f"  {winner.prize_order}. {winner.user.name} ({winner.user.department})")

    def _show_summary(self) -> None:
        if self.results is None:
            print("No lottery has been run yet.")
            return
        self._print_summary(self.prize_manager.get_prizes())

    def _export_results(self) -> None:
        if self.results is None:
            print("No lottery results to export. Run the lottery first.")
            return
        success, message = self.results.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    """Entry point for the interactive lottery system."""
    try:
        LotterySystemCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExited.")
