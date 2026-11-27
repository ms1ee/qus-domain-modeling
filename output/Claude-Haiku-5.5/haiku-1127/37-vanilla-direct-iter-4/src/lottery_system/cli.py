"""Command-line interface for the lottery system."""

from lottery_system.config import DRAWER_LI_BIN
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import prize_level


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive menu-driven controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_prizes: list[Prize] = []

    # ----- main loop ----------------------------------------------------

    MENU = [
        ("1", "Load default participant list"),
        ("2", "Load custom participant list (txt)"),
        ("3", "View department groups and counts"),
        ("4", "Load default prize library"),
        ("5", "Add custom prize"),
        ("6", "View prize list"),
        ("7", "Reorder prizes"),
        ("8", "Start lottery"),
        ("9", "View and export results"),
        ("0", "Exit"),
    ]

    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        handlers = {
            "1": self._load_default_list,
            "2": self._load_custom_list,
            "3": self._view_groups,
            "4": self._load_default_prizes,
            "5": self._add_prize,
            "6": self._view_prizes,
            "7": self._reorder_prizes,
            "8": self._start_lottery,
            "9": self._export_results,
        }
        while True:
            print()
            for key, label in self.MENU:
                print(f"  [{key}] {label}")
            choice = input("Select an option: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            handler = handlers.get(choice)
            if handler is None:
                print("Invalid option, please try again.")
                continue
            handler()

    # ----- list management ----------------------------------------------

    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        valid, duplicates = self.list_manager.validate_users(users)
        for error in errors:
            print(error)
        if duplicates:
            print(f"Ignored {len(duplicates)} duplicate entries in the default list.")
        self.users = valid
        print(f"Default participant list loaded: {len(self.users)} people.")

    def _load_custom_list(self) -> None:
        path = input("Enter the path of the txt list file: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)

        if errors:
            print("Problems found in the uploaded list:")
            for error in errors:
                print(f"  - {error}")
            if not self._confirm_removal("invalid data"):
                print("Upload terminated. Current participant list unchanged.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print("Duplicate names detected:")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
            if not self._confirm_removal("duplicate entries"):
                print("Upload terminated. Current participant list unchanged.")
                return

        if not valid:
            print("No valid participants found. Upload cancelled.")
            return

        self.users = valid
        print(f"Custom participant list loaded: {len(self.users)} people.")

    @staticmethod
    def _confirm_removal(label: str) -> bool:
        while True:
            answer = input(
                f"Enter 'r' to remove {label} and continue, or 'a' to abort the upload: "
            ).strip().lower()
            if answer == "r":
                return True
            if answer == "a":
                return False
            print("Please enter 'r' or 'a'.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded. Please load a list first.")
            return
        groups = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for department, count in groups.items():
            print(f"  - {department}: {count} people")

    # ----- prize management ---------------------------------------------

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            print(error)
        print("Default prize library loaded.")

    def _add_prize(self) -> None:
        name = input("Prize name: ").strip()
        quantity_text = input("Prize quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be an integer.")
            return

        if self.users:
            groups = list(self.list_manager.get_group_info(self.users).keys())
            print("Available department groups: " + ", ".join(groups))
        groups_text = input("Avoidance groups (comma-separated, blank for none): ")
        avoid_groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        drawer = input("Associated lottery person (blank for none): ").strip() or None

        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print(f"Prize '{name}' added.")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize list (lottery order):")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = input("Enter the new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery process ----------------------------------------------

    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self.lottery is not None and self.lottery.result_manager.get_winners():
            answer = input("Previous results exist. Restart and clear them? (y/n): ").strip().lower()
            if answer != "y":
                print("Lottery cancelled.")
                return

        lottery = LotteryManager(self.users)
        self.lottery = lottery
        self.lottery_prizes = prizes

        total_rounds = len(prizes)
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(lottery, prize, round_no, total_rounds)

        print()
        print("=" * 60)
        print("  Final Winner List")
        print("=" * 60)
        self._print_sorted_results(lottery, prizes)

    def _run_round(self, lottery: LotteryManager, prize: Prize, round_no: int, total_rounds: int) -> None:
        print()
        print("-" * 60)
        print(f"Round {round_no}/{total_rounds}")
        print(f"Prize: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Lottery person: {prize.associated_drawer or 'None'}")
        print(f"Rule: {lottery.describe_rule(prize)}")
        print("-" * 60)

        lottery.start_round(prize)
        drawn = 0
        terminated = False

        while drawn < prize.quantity:
            if not lottery.eligible_candidates(prize):
                print("No eligible candidates remain for this prize. Round ends early.")
                break

            command = input(
                "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            ).strip().lower()
            if command == "terminate":
                terminated = True
                break
            if command == "pause":
                print("Lottery paused.")
                while True:
                    resume = input("Type 'continue' to resume or 'terminate' to end this round: ").strip().lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        break
                    if resume == "terminate":
                        terminated = True
                        break
                    print("Unknown command.")
                if terminated:
                    break
            elif command not in ("", "continue"):
                print("Unknown command. Press Enter to draw, or type 'pause' / 'terminate'.")
                continue

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = lottery.draw_winner(prize)
            if user is None:
                print("No eligible candidates remain for this prize. Round ends early.")
                break
            drawn += 1
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        winners = lottery.finish_round(prize)
        print()
        if terminated:
            print("Round terminated early.")
        print(f"Round results for {prize.name} ({len(winners)} winner(s)):")
        if not winners:
            print("  (no winners)")
        for index, user in enumerate(winners, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    def _print_sorted_results(self, lottery: LotteryManager, prizes: list[Prize]) -> None:
        winners = lottery.result_manager.get_sorted_winners(prizes)
        if not winners:
            print("No winners recorded.")
            return
        current_prize = None
        for winner in winners:
            if winner.prize_name != current_prize:
                current_prize = winner.prize_name
                print(f"\n{current_prize}:")
            print(f"  #{winner.sequence} {winner.user.name} ({winner.user.department})")

    # ----- results ------------------------------------------------------

    def _export_results(self) -> None:
        if self.lottery is None or not self.lottery.result_manager.get_winners():
            print("No lottery results to display or export yet.")
            return
        self._print_sorted_results(self.lottery, self.lottery_prizes)
        success, message = self.lottery.result_manager.export_to_csv(self.lottery_prizes)
        print(message)


def main() -> None:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
