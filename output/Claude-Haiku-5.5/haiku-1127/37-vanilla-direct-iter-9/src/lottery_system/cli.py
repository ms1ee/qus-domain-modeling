"""Command-line interface for the lottery system."""
from lottery_system.config import DEFAULT_DRAW_DELAY, DRAWERS
from lottery_system.console import InputReader
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager
from lottery_system.utils import ordinal

BANNER = "=" * 60 + "\n   Company Team Building - Smart Lottery System\n" + "=" * 60


class LotteryApp:
    """Interactive controller for the whole application."""

    def __init__(self, reader: InputReader | None = None, draw_delay: float = DEFAULT_DRAW_DELAY):
        self.reader = reader or InputReader()
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.last_results: ResultManager | None = None
        self.last_prizes: list[Prize] = []

    # ------------------------------------------------------------------ utils
    def _prompt(self, text: str) -> str | None:
        return self.reader.prompt(text)

    @staticmethod
    def _print_main_menu() -> None:
        print()
        print("---------------- Main Menu ----------------")
        print("1. Load default team building list")
        print("2. Upload custom txt list")
        print("3. View department groups")
        print("4. Manage prizes")
        print("5. Reorder prizes")
        print("6. Start lottery")
        print("7. Export results")
        print("0. Exit")

    # -------------------------------------------------------------- main loop
    def run(self) -> None:
        print(BANNER)
        while True:
            self._print_main_menu()
            choice = self._prompt("Select an option: ")
            if choice is None:
                print("Input closed. Exiting.")
                break
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._upload_custom_list()
            elif choice == "3":
                self._show_groups()
            elif choice == "4":
                self._manage_prizes()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "6":
                self._start_lottery()
            elif choice == "7":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option. Please try again.")

    # ------------------------------------------------------------ list module
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._apply_loaded_list(users, errors)

    def _upload_custom_list(self) -> None:
        path = self._prompt("Enter the path of the txt file (each line: Name,Department Group): ")
        if path is None:
            return
        path = path.strip().strip('"').strip("'")
        if not path:
            print("No file path given. Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._apply_loaded_list(users, errors)

    def _apply_loaded_list(self, users: list[User], errors: list[str]) -> None:
        if errors:
            print("Problems found in the list:")
            for error in errors:
                print(f"  - {error}")
        valid, duplicates = self.list_manager.validate_users(users)
        for dup in duplicates:
            print(f"  - Duplicate Name: '{dup.name}' ({dup.department}) already exists in the list.")

        if errors or duplicates:
            print(f"Valid records: {len(valid)} | invalid or duplicate records: "
                  f"{len(errors) + len(duplicates)}")
            choice = self._prompt(
                "Enter 'r' to remove invalid data and continue, or 't' to terminate the upload: "
            )
            if choice is None or choice.lower() != "r":
                print("Upload terminated. Current list unchanged.")
                return

        if not valid:
            print("No valid users found. Current list unchanged.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} users.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No user list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self.users)} people in {len(info)} groups.")

    # ----------------------------------------------------------- prize module
    def _manage_prizes(self) -> None:
        while True:
            print()
            print("---------------- Prize Library ----------------")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes")
            print("0. Back")
            choice = self._prompt("Select an option: ")
            if choice is None or choice == "0":
                return
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  - {error}")
                if not errors:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            else:
                print("Invalid option. Please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "None"
            avoid = ", ".join(prize.avoid_groups) or "None"
            print(f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                  f"Lottery person: {drawer} | Avoid groups: {avoid}")

    def _add_custom_prize(self) -> None:
        name = self._prompt("Prize name (blank to cancel): ")
        if not name:
            print("Cancelled.")
            return

        quantity = None
        while quantity is None:
            text = self._prompt("Quantity (positive integer, blank to cancel): ")
            if not text:
                print("Cancelled.")
                return
            try:
                value = int(text)
                if value < 1:
                    raise ValueError
                quantity = value
            except ValueError:
                print("Please enter a positive integer.")

        drawer = self._choose_drawer()
        if drawer is False:
            print("Cancelled.")
            return

        avoid_groups = self._choose_avoid_groups()
        if avoid_groups is None:
            print("Cancelled.")
            return

        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print(f"Prize '{name.strip()}' added.")

    def _choose_drawer(self):
        """Return drawer name, None for no drawer, or False if cancelled."""
        print("Associated lottery person:")
        print("  0. None")
        for index, drawer in enumerate(DRAWERS, start=1):
            print(f"  {index}. {drawer}")
        print(f"  {len(DRAWERS) + 1}. Other (type a name)")
        text = self._prompt("Choose a number or type a name (blank for none): ")
        if text is None:
            return False
        if text == "" or text == "0":
            return None
        if text.isdigit():
            number = int(text)
            if 1 <= number <= len(DRAWERS):
                return DRAWERS[number - 1]
            if number == len(DRAWERS) + 1:
                other = self._prompt("Enter lottery person name (blank for none): ")
                if other is None:
                    return False
                return other.strip() or None
            print("Invalid choice; no lottery person set.")
            return None
        return text.strip() or None

    def _choose_avoid_groups(self) -> list[str] | None:
        options: list[str] = []
        if self.users:
            options = list(self.list_manager.get_group_info(self.users).keys())
            print("Available department groups:")
            for index, group in enumerate(options, start=1):
                print(f"  {index}. {group}")
        text = self._prompt(
            "Avoid groups (comma-separated numbers or names, blank for none): "
        )
        if text is None:
            return None
        groups: list[str] = []
        for token in text.split(","):
            item = token.strip()
            if not item:
                continue
            if item.isdigit() and options and 1 <= int(item) <= len(options):
                group = options[int(item) - 1]
            else:
                group = item
            if group not in groups:
                groups.append(group)
        return groups

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._prompt(
            "Enter the new order as serial numbers separated by spaces (e.g. 2 1 3): "
        )
        if text is None or not text.strip():
            print("Reorder cancelled.")
            return
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self._show_prizes()
        else:
            print("Invalid order: every prize serial number must appear exactly once.")

    # ------------------------------------------------------- lottery process
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a user list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return

        lottery = LotteryManager(self.users)
        results = ResultManager()
        print()
        print("=== Lottery started ===")
        print("Commands during the lottery: 'pause', 'continue', 'terminate'")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, prize, lottery, results)

        self.last_results = results
        self.last_prizes = prizes
        self._print_final_summary(results, prizes)

    def _run_round(self, round_no: int, prize: Prize, lottery: LotteryManager,
                   results: ResultManager) -> None:
        print()
        print(f"=== Round {round_no}: {prize.name} ===")
        print(f"Quantity: {prize.quantity} | Lottery person: {prize.associated_drawer or 'None'}")
        print(f"Rule: {lottery.describe_rule(prize)}")

        if lottery.eligible_count(prize) == 0:
            print("No eligible candidates for this round. Round skipped.")
            return

        round_winners: list[User] = []
        for position in range(1, prize.quantity + 1):
            if self._process_controls(wait=self.draw_delay):
                print(f"Round ended early. Winners drawn: {len(round_winners)}/{prize.quantity}")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this round.")
                break
            results.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        print(f"--- Round {round_no} results ---")
        if not round_winners:
            print("  (no winners)")
        for index, user in enumerate(round_winners, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    def _process_controls(self, wait: float) -> bool:
        """Wait up to `wait` seconds, processing control commands.

        Returns True if the current round must be terminated.
        """
        ok, line = self.reader.poll(wait)
        while ok:
            command = (line or "").strip().lower()
            if command == "pause":
                if self._wait_while_paused():
                    return True
            elif command == "terminate":
                print("Terminate command received: ending the current round.")
                return True
            elif command == "continue":
                print("Lottery is not paused.")
            elif command:
                print(f"Unknown command '{line}'. Available: pause, continue, terminate.")
            ok, line = self.reader.poll(0.0)
        return False

    def _wait_while_paused(self) -> bool:
        """Block while paused. Returns True if the round should be terminated."""
        print("Lottery PAUSED. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            ok, line = self.reader.poll(None)
            if not ok:
                print("Input closed: ending the current round.")
                return True
            command = (line or "").strip().lower()
            if command == "continue":
                print("Lottery resumed.")
                return False
            if command == "terminate":
                print("Current round terminated.")
                return True
            if command == "pause":
                print("Lottery is already paused.")
            elif command:
                print("While paused, only 'continue' or 'terminate' is accepted.")

    def _print_final_summary(self, results: ResultManager, prizes: list[Prize]) -> None:
        print()
        print("=== Final Winner List (by prize level, then winning order) ===")
        grouped = results.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            print("No winners were drawn.")
            return
        for prize_name, winners in grouped.items():
            print(f"[{prize_name}] ({len(winners)})")
            for index, winner in enumerate(winners, start=1):
                print(f"  {index}. {winner.user.name} ({winner.user.department})")
        print("=== Lottery finished ===")

    # ----------------------------------------------------------- export
    def _export_results(self) -> None:
        if self.last_results is None:
            print("No lottery results to export. Please run the lottery first.")
            return
        _, message = self.last_results.export_to_csv(self.last_prizes)
        print(message)


def main() -> int:
    app = LotteryApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
