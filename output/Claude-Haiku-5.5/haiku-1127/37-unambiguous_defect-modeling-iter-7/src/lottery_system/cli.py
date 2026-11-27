"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    MENU = """
========== Team Building Smart Lottery ==========
1. Load built-in default team list
2. Upload custom txt list
3. View department groups
4. Prize configuration
5. Start lottery
6. View winner list
7. Export winner list (txt/CSV)
0. Exit
"""

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.list_loaded = False
        self.result_manager = None
        self.last_prizes = []

    # ------------------------------------------------------------------ main
    def run(self):
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            print(self.MENU)
            choice = input("Select an option: ").strip()
            if choice == "1":
                self.load_default_list()
            elif choice == "2":
                self.load_custom_list()
            elif choice == "3":
                self.view_groups()
            elif choice == "4":
                self.prize_menu()
            elif choice == "5":
                self.start_lottery()
            elif choice == "6":
                self.view_results()
            elif choice == "7":
                self.export_results()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------------ list menu
    def load_default_list(self):
        users, errors = self.list_manager.load_default_list()
        self._show_errors(errors)
        self._apply_users(users)

    def load_custom_list(self):
        path = input("Enter the path of the txt file: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        if errors:
            print("Validation found the following issues:")
            self._show_errors(errors)
            if not users:
                print("No valid entries found. Upload terminated.")
                return
            answer = input(
                f"Remove invalid entries and continue with {len(users)} valid entries? "
                "(y = continue / n = terminate upload): "
            ).strip().lower()
            if answer != "y":
                print("Upload terminated. Current list unchanged.")
                return
        self._apply_users(users)

    def _apply_users(self, users):
        self.users = list(users)
        self.list_loaded = True
        print(f"List loaded successfully with {len(self.users)} valid entries.")

    def view_groups(self):
        if not self.list_loaded:
            print("Please load a list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No department groups found.")
            return
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")

    # ----------------------------------------------------------- prize menu
    def prize_menu(self):
        while True:
            print(
                "\n---------- Prize Configuration ----------\n"
                "1. View prizes\n"
                "2. Add custom prize\n"
                "3. Load preset prize library\n"
                "4. Reorder lottery rounds\n"
                "0. Back"
            )
            choice = input("Select an option: ").strip()
            if choice == "1":
                self._print_prizes()
            elif choice == "2":
                self._add_prize_interactive()
            elif choice == "3":
                self._show_errors(self.prize_manager.load_default_prizes())
                print("Preset prizes loaded.")
            elif choice == "4":
                self._reorder_interactive()
            elif choice == "0":
                break
            else:
                print("Invalid option, please try again.")

    def _print_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            print(
                f"{index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {prize.associated_drawer or 'None'} | "
                f"avoid groups: {groups}"
            )

    def _add_prize_interactive(self):
        name = input("Prize name: ").strip()
        quantity_text = input("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Error: quantity must be an integer.")
            return
        groups_text = input("Avoidance groups (comma-separated, empty for none): ")
        groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        if groups and self.list_loaded:
            known = set(self.list_manager.get_group_info(self.users))
            unknown = [group for group in groups if group not in known]
            if unknown:
                print(f"Warning: these groups are not in the current list: {', '.join(unknown)}")
        drawer = input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def _reorder_interactive(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes to reorder.")
            return
        self._print_prizes()
        raw = input("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ").split()
        try:
            order = [int(item) for item in raw]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery round order updated.")
            self._print_prizes()
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # -------------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.list_loaded or not self.users:
            print("Please load a valid employee list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please configure prizes first.")
            return
        if self.result_manager and self.result_manager.get_all_winners():
            answer = input("Previous results will be replaced. Continue? (y/n): ").strip().lower()
            if answer != "y":
                return

        lottery = LotteryManager(self.users)
        results = ResultManager()
        self.result_manager = results
        self.last_prizes = prizes

        print("\n========== Lottery Started ==========")
        print("Commands: [Enter] draw next | 'pause' | 'terminate' (skip current round)")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, prize, lottery, results)
        print("\n========== All rounds completed ==========")
        self.show_summary(prizes)

    def _run_round(self, index, prize, lottery, results):
        print(f"\n----- Round {index}: {prize.name} -----")
        print(f"Quantity: {prize.quantity}")
        print("Rules:")
        for rule in lottery.describe_rules(prize):
            print(f"  - {rule}")

        round_winners = []
        for position in range(1, prize.quantity + 1):
            if not lottery.get_eligible_pool(prize):
                print("No eligible candidates remain for this prize. Round ends early.")
                break
            print(f"Currently drawing the {_ordinal(position)} winner...")
            command = self._await_command()
            if command == "terminate":
                print("Current round terminated by operator. Skipping to next round.")
                break
            winner = lottery.draw_one(prize)
            if winner is None:
                print("No eligible candidates remain for this prize. Round ends early.")
                break
            results.add_winner(winner, prize)
            round_winners.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")

        lottery.finish_round(prize, round_winners)

        if round_winners:
            print(f"Round {index} results:")
            for order, winner in enumerate(round_winners, start=1):
                print(f"  {order}. {winner.name} ({winner.department})")
        else:
            print(f"Round {index} produced no winners.")

    def _await_command(self):
        """Wait for operator input. Returns 'draw' or 'terminate'."""
        while True:
            command = input("[Enter] draw next | 'pause' | 'terminate': ").strip().lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = input("(paused) > ").strip().lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if resume == "terminate":
                        return "terminate"
                    print("Please type 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # -------------------------------------------------------------- results
    def show_summary(self, prizes):
        if not self.result_manager:
            print("No lottery results yet.")
            return
        winners = self.result_manager.get_ordered_winners(prizes)
        print("\n========== Winner List ==========")
        if not winners:
            print("No winners.")
            return
        for winner in winners:
            print(
                f"[{winner.prize_name}] {winner.user.name} ({winner.user.department}) "
                f"- winning order #{winner.winning_order}"
            )

    def view_results(self):
        if not self.result_manager or not self.result_manager.get_all_winners():
            print("No results yet. Run a lottery first.")
            return
        self.show_summary(self.last_prizes)

    def export_results(self):
        if not self.result_manager or not self.result_manager.get_all_winners():
            print("No results to export. Run a lottery first.")
            return
        _, message = self.result_manager.export_to_csv(self.last_prizes)
        print(message)

    # ---------------------------------------------------------------- utils
    @staticmethod
    def _show_errors(errors):
        if errors:
            print("Issues detected:")
            for error in errors:
                print(f"  - {error}")


def main():
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")


if __name__ == "__main__":
    main()
