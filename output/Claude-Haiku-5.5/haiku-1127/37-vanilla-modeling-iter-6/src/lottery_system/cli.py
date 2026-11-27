"""Command-line interface for the lottery system."""

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.has_results = False

    # ----- utilities -----------------------------------------------------
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _print_menu(self) -> None:
        print("\n========== Team Building Smart Lottery ==========")
        print("1. Load built-in default team building list")
        print("2. Load custom txt list (Name,Department Group per line)")
        print("3. View department groups")
        print("4. Load preset prizes")
        print("5. Add custom prize")
        print("6. View and reorder prizes")
        print("7. Start lottery")
        print("8. View winner list")
        print("9. Export winner list to file")
        print("0. Exit")

    def run(self) -> None:
        print("Welcome to the Company Team Building Smart Lottery System.")
        while True:
            self._print_menu()
            try:
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self._load_default_list()
                elif choice == "2":
                    self._load_custom_list()
                elif choice == "3":
                    self._view_groups()
                elif choice == "4":
                    self._load_presets()
                elif choice == "5":
                    self._add_prize()
                elif choice == "6":
                    self._view_and_reorder_prizes()
                elif choice == "7":
                    self._start_lottery()
                elif choice == "8":
                    self._view_winners()
                elif choice == "9":
                    self._export_results()
                elif choice == "0":
                    print("Goodbye!")
                    return
                else:
                    print("Invalid option, please try again.")
            except (EOFError, KeyboardInterrupt):
                print("\nInput closed. Exiting.")
                return

    # ----- list management ----------------------------------------------
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._apply_loaded_list(users, errors, "built-in default list")

    def _load_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file: ")
        if not path:
            print("No path entered. Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._apply_loaded_list(users, errors, f"file '{path}'")

    def _apply_loaded_list(self, users: list[User], errors: list[str], source: str) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self.users = valid
            print(f"Loaded {len(valid)} participants from {source}.")
            return

        print(f"Verification of {source} found issues:")
        for error in errors:
            print(f"  {error}")
        for dup in duplicates:
            print(f"  Duplicate Name: '{dup.name}' ({dup.department}) already exists, ignored.")
        print(f"Valid participants: {len(valid)}")
        print("1. Remove invalid data and keep valid participants")
        print("2. Terminate upload")
        choice = self._ask("Select an option: ")
        if choice == "1":
            if not valid:
                print("No valid participants remain. Participant list unchanged.")
                return
            self.users = valid
            print(f"Loaded {len(valid)} participants from {source}.")
        else:
            print("Upload terminated. Participant list unchanged.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current department groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} people")
        print(f"Total participants: {len(self.users)}")

    # ----- prize management ---------------------------------------------
    def _load_presets(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(error)
        else:
            print("Preset prizes loaded.")

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be a positive integer.")
            return

        groups = sorted({u.department for u in self.users})
        avoid: list[str] = []
        if groups:
            print("Available department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        raw_avoid = self._ask(
            "Avoidance groups (serial numbers or names, comma-separated, blank for none): "
        )
        for token in [t.strip() for t in raw_avoid.split(",") if t.strip()]:
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                avoid.append(groups[int(token) - 1])
            else:
                avoid.append(token)

        drawer = self._ask("Associated lottery person (blank for none): ")
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid, drawer or None)
            print(f"Prize added: {prize.name} (quantity {prize.quantity}).")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _view_and_reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes(prizes)
        raw = self._ask(
            "Enter new order as serial numbers separated by spaces (blank to keep): "
        )
        if not raw:
            return
        try:
            order = [int(token) for token in raw.split()]
        except ValueError:
            print("Invalid order: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self._print_prizes(self.prize_manager.get_prizes())
        else:
            print("Invalid order: every serial number must be used exactly once.")

    @staticmethod
    def _print_prizes(prizes) -> None:
        print("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid: {avoid} | Lottery person: {drawer}"
            )

    # ----- lottery process ----------------------------------------------
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        self.result_manager = ResultManager()
        self.has_results = False
        lottery = LotteryManager(self.users)
        print("\nLottery begins!")
        print("Commands: [Enter] draw next winner | pause | terminate (end current round)")

        for round_no, prize in enumerate(prizes, start=1):
            print(f"\n--- Round {round_no}: {prize.name} ---")
            print(f"Quantity: {prize.quantity}")
            print(f"Rule: {lottery.describe_rule(prize)}")
            print(f"Eligible participants at start: {lottery.pool_size(prize)}")
            round_winners = self._run_round(lottery, prize)
            print(f"Round {round_no} results:")
            if not round_winners:
                print("  (no winners in this round)")
            for winner in round_winners:
                print(
                    f"  #{winner.winning_order} {winner.user.name} "
                    f"({winner.user.department}) - {prize.name}"
                )

        self.has_results = True
        print("\nAll rounds completed.")
        self._print_summary(prizes)

    def _run_round(self, lottery: LotteryManager, prize) -> list[Winner]:
        lottery.start_round(prize)
        round_winners: list[Winner] = []
        drawn = 0
        while drawn < prize.quantity:
            print(f"Currently drawing the {_ordinal(drawn + 1)} winner...")
            if self._await_action() == "terminate":
                print("Round terminated manually; remaining winners are skipped.")
                break
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize; round ends early.")
                break
            drawn += 1
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")
        lottery.end_round(prize)
        return round_winners

    def _await_action(self) -> str:
        """Returns 'draw' or 'terminate'. Handles pause/continue commands."""
        while True:
            command = self._ask("Press Enter to draw (or type pause / terminate): ").lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("(paused) > ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if resume == "terminate":
                        return "terminate"
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _print_summary(self, prizes) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n========== Final Winner List ==========")
        for prize_name, winners in grouped.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  #{winner.winning_order} {winner.user.name} "
                    f"({winner.user.department}) at "
                    f"{winner.winning_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

    # ----- results ------------------------------------------------------
    def _view_winners(self) -> None:
        if not self.has_results:
            print("No lottery results yet.")
            return
        self._print_summary(self.prize_manager.get_prizes())

    def _export_results(self) -> None:
        if not self.has_results:
            print("No lottery results to export.")
            return
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    LotterySystemCLI().run()
