import re

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

SEPARATOR = "=" * 60


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ----- main loop -----------------------------------------------------

    def run(self):
        print(SEPARATOR)
        print("Company Team Building - Smart Lottery System")
        print(SEPARATOR)
        actions = {
            "1": self._load_list,
            "2": self._show_groups,
            "3": self._load_default_prizes,
            "4": self._add_custom_prize,
            "5": self._show_prizes,
            "6": self._reorder_prizes,
            "7": self._start_lottery,
            "8": self._show_summary,
            "9": self._export,
        }
        while True:
            self._print_menu()
            choice = input("Select an option: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid option, please try again.")
                continue
            action()

    def _print_menu(self):
        print()
        print("1. Load team building list (default / custom txt)")
        print("2. View department groups and headcounts")
        print("3. Load default prize library")
        print("4. Add custom prize")
        print("5. Show prize list")
        print("6. Adjust prize order")
        print("7. Start lottery")
        print("8. Show winner summary")
        print("9. Export winner list to file")
        print("0. Exit")

    # ----- list management ----------------------------------------------

    def _load_list(self):
        if self.result_manager.get_all_winners():
            print("Cannot reload the list after winners have been drawn.")
            return
        print("1. Built-in default list")
        print("2. Custom txt file (each line: Name,Department Group)")
        choice = input("Select list source: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = input("Enter txt file path: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid option.")
            return

        valid = self._review_list(users, errors)
        if valid is None:
            return
        self.users = valid
        self.lottery = LotteryManager(self.users, self.result_manager)
        print(f"Loaded {len(self.users)} valid participant(s).")

    def _review_list(self, users, errors):
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            if not valid:
                print("The list is empty.")
                return None
            return valid

        for error in errors:
            print(error)
        for dup in duplicates:
            print(f"Duplicate Name: {dup.name} ({dup.department}) appears more than once and will be ignored.")

        while True:
            choice = input(
                "Type 'remove' to drop invalid data and continue, "
                "or 'terminate' to cancel the upload: "
            ).strip().lower()
            if choice == "remove":
                if not valid:
                    print("No valid data remains.")
                    return None
                return valid
            if choice == "terminate":
                print("Upload terminated.")
                return None
            print("Please enter 'remove' or 'terminate'.")

    def _show_groups(self):
        if not self.users:
            print("No list loaded. Please use option 1 first.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self.users)} people")

    # ----- prize management ---------------------------------------------

    def _load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(error)
        else:
            print("Default prize library loaded.")

    def _add_custom_prize(self):
        name = input("Prize name: ").strip()
        quantity_raw = input("Quantity: ").strip()
        try:
            quantity = int(quantity_raw)
        except ValueError:
            print("Quantity must be an integer.")
            return
        if self.users:
            groups = ", ".join(self.list_manager.get_group_info(self.users).keys())
            print(f"Available groups: {groups}")
        avoid_raw = input("Avoidance groups (comma separated, blank for none): ")
        drawer = input("Associated lottery person (blank for none): ").strip()
        avoid = [group.strip() for group in avoid_raw.split(",") if group.strip()]
        try:
            self.prize_manager.add_prize(name, quantity, avoid, drawer or None)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print("Prize added.")

    def _show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(f"{index}. {prize.name} | quantity: {prize.quantity} | "
                  f"lottery person: {drawer} | avoid groups: {avoid}")

    def _reorder_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        raw = input("Enter new order as serial numbers (e.g. 2 1 3): ").strip()
        try:
            order = [int(item) for item in re.split(r"[\s,]+", raw) if item]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery process ----------------------------------------------

    def _start_lottery(self):
        if self.lottery is None or not self.users:
            print("Please load the team building list first (option 1).")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please load or add prizes first.")
            return
        print(f"Lottery starts with {len(prizes)} round(s).")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)
        print("\nAll lottery rounds completed.")
        self._print_summary(prizes)

    def _run_round(self, index: int, total: int, prize):
        print()
        print(SEPARATOR)
        print(f"Round {index}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print("Rules:")
        for rule in self.lottery.describe_rules(prize):
            print(f"  - {rule}")
        print(SEPARATOR)

        drawn: list[User] = []
        for position in range(1, prize.quantity + 1):
            action = self._await_control(position)
            if action == "terminate":
                print("Round terminated. Skipping the remaining winners of this prize.")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            drawn.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.lottery.finish_round(prize, drawn)
        print(f"Round {index} results ({prize.name}):")
        if drawn:
            for number, user in enumerate(drawn, start=1):
                print(f"  {number}. {user.name} ({user.department})")
        else:
            print("  No winners in this round.")

    def _await_control(self, position: int) -> str:
        """Wait for user control input before the next draw. Returns 'draw' or 'terminate'."""
        while True:
            command = input(
                f"[Enter] draw winner #{position} | 'pause' | 'terminate': "
            ).strip().lower()
            if command in ("", "continue"):
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

    # ----- results ------------------------------------------------------

    def _print_summary(self, prizes):
        grouped = self.result_manager.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            print("No winners yet.")
            return
        print()
        print(SEPARATOR)
        print("Winner summary (by prize level, then winning order)")
        print(SEPARATOR)
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"\n{prize_name} ({len(winners)} winner(s))")
            for number, winner in enumerate(winners, start=1):
                print(f"  {number}. {winner.user.name} ({winner.user.department}) - {winner.won_at}")

    def _show_summary(self):
        self._print_summary(self.prize_manager.get_prizes())

    def _export(self):
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main():
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting the lottery system.")
