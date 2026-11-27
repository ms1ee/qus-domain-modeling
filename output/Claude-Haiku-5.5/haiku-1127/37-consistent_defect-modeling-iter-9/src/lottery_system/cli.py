"""Command-line interface controlling the lottery process."""
from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

MENU = """
========== Team Building Smart Lottery ==========
 1. Load default participant list
 2. Upload custom participant list (txt)
 3. View department groups
 4. Load default prize library
 5. Add custom prize
 6. View prize sequence
 7. Reorder prize sequence
 8. Start lottery
 9. Export winner list
 0. Exit
================================================"""


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller for the whole lottery workflow."""

    def __init__(self) -> None:
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._results: ResultManager | None = None
        self._last_prizes: list[Prize] = []

    def run(self) -> None:
        """Main menu loop."""
        print("Welcome to the Team Building Smart Lottery System.")
        handlers = {
            "1": self._load_default_participants,
            "2": self._upload_custom_participants,
            "3": self._view_groups,
            "4": self._load_default_prizes,
            "5": self._add_custom_prize,
            "6": self._view_prizes,
            "7": self._reorder_prizes,
            "8": self._start_lottery,
            "9": self._export_results,
        }
        while True:
            print(MENU)
            choice = input("Select an option: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            handler = handlers.get(choice)
            if handler is None:
                print("Invalid option, please try again.")
                continue
            handler()

    # ----- participant list -------------------------------------------------

    def _load_default_participants(self) -> None:
        users, errors = self._list_manager.load_default_list()
        self._accept_participants(users, errors, "default list")

    def _upload_custom_participants(self) -> None:
        path = input("Enter the path of the txt file (Name,Department per line): ").strip().strip('"')
        if not path:
            print("Upload cancelled.")
            return
        users, errors = self._list_manager.load_custom_list(path)
        self._accept_participants(users, errors, path)

    def _accept_participants(self, users: list[User], errors: list[str], source: str) -> None:
        """Verify parsed users and let the operator decide how to handle problems."""
        valid_users, duplicates = self._list_manager.validate_users(users)
        if not errors and not duplicates:
            self._set_participants(valid_users)
            return

        print(f"Verification of '{source}' found problems:")
        for error in errors:
            print(f"  - {error}")
        for duplicate in duplicates:
            print(f"  - Duplicate name: {duplicate.name} ({duplicate.department})")

        while True:
            choice = input(
                "Enter 'r' to remove invalid/duplicate data and continue, "
                "or 't' to terminate the upload: "
            ).strip().lower()
            if choice == "r":
                if not valid_users:
                    print("No valid data remains; upload terminated.")
                    return
                self._set_participants(valid_users)
                return
            if choice == "t":
                print("Upload terminated; participant list unchanged.")
                return
            print("Please enter 'r' or 't'.")

    def _set_participants(self, users: list[User]) -> None:
        self._users = list(users)
        print(f"Loaded {len(self._users)} participants.")
        self._view_groups()

    def _view_groups(self) -> None:
        if not self._users:
            print("No participant list loaded.")
            return
        print("Department groups:")
        for department, count in self._list_manager.get_group_info(self._users).items():
            print(f"  {department}: {count} people")

    # ----- prizes -----------------------------------------------------------

    def _load_default_prizes(self) -> None:
        errors = self._prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(f"  - {error}")
        else:
            print("Default prize library loaded.")

    def _add_custom_prize(self) -> None:
        name = input("Prize name: ").strip()
        quantity_text = input("Quantity: ").strip()
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            print("Quantity must be a positive integer.")
            return
        if self._users:
            print("Available groups: " + ", ".join(self._list_manager.get_group_info(self._users)))
        groups_text = input("Avoidance groups (comma separated, optional): ").strip()
        avoid_groups = [g.strip() for g in groups_text.split(",") if g.strip()]
        drawer = input("Associated lottery person (optional): ").strip() or None
        try:
            prize = self._prize_manager.add_prize(name, int(quantity_text), avoid_groups, drawer)
        except ValueError as exc:
            print(f"Could not add prize: {exc}")
            return
        position = len(self._prize_manager.get_prizes())
        print(f"Prize '{prize.name}' added at sequence position {position}.")

    def _view_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} | Quantity: {prize.quantity}")
            print(f"     Rule: {prize.rule_description}")

    def _reorder_prizes(self) -> None:
        if not self._prize_manager.get_prizes():
            print("No prizes configured.")
            return
        self._view_prizes()
        text = input("Enter the new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(item) for item in text.split()]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if not self._prize_manager.reorder_prizes(order):
            print("Invalid order: each current serial number must appear exactly once.")
            return
        print("Prize sequence updated.")
        self._view_prizes()

    # ----- lottery process --------------------------------------------------

    def _start_lottery(self) -> None:
        if not self._users:
            print("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self._users)
        results = ResultManager()
        self._results = results
        self._last_prizes = prizes

        print("\nLottery started. Commands during draws: [Enter] draw, 'pause', 'terminate'.")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, len(prizes), lottery, results, prize)

        self._print_final_results(prizes, results)

    def _run_round(
        self,
        round_no: int,
        total_rounds: int,
        lottery: LotteryManager,
        results: ResultManager,
        prize: Prize,
    ) -> None:
        print("\n" + "-" * 60)
        print(f"Round {round_no}/{total_rounds}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {prize.rule_description}")
        print("-" * 60)

        round_winners: list[Winner] = []
        for position in range(1, prize.quantity + 1):
            if self._await_command(position) == "terminate":
                print("Round terminated by operator; remaining winners are skipped.")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = lottery.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize; the round ends.")
                break
            winner = results.add_winner(user, prize)
            round_winners.append(winner)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"\nResults of round {round_no}:")
        if not round_winners:
            print("  (no winners)")
        for winner in round_winners:
            print(
                f"  #{winner.winning_order}: {winner.user.name} "
                f"({winner.user.department}) - {prize.name}"
            )

    def _await_command(self, position: int) -> str:
        """Wait for the operator before the next draw. Returns 'draw' or 'terminate'."""
        while True:
            command = input(
                f"[Enter] draw the {ordinal(position)} winner | 'pause' | 'terminate': "
            ).strip().lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused.")
                while True:
                    resume = input("Type 'continue' to resume or 'terminate' to end this round: ").strip().lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        break
                    if resume == "terminate":
                        return "terminate"
                    print("Unknown command.")
                continue
            print("Unknown command.")

    def _print_final_results(self, prizes: list[Prize], results: ResultManager) -> None:
        print("\n========== Final Winner List ==========")
        for prize_name, winners in results.get_winners_by_prize(prizes).items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  #{winner.winning_order}: {winner.user.name} "
                    f"({winner.user.department}) at {winner.winning_time:%H:%M:%S}"
                )
        print("=======================================")

    # ----- export -----------------------------------------------------------

    def _export_results(self) -> None:
        if self._results is None or not self._results.get_winners():
            print("No lottery results to export. Run the lottery first.")
            return
        _, message = self._results.export_to_csv(self._last_prizes)
        print(message)


def main() -> int:
    """Program entry point."""
    try:
        LotteryCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting the lottery system.")
    return 0
