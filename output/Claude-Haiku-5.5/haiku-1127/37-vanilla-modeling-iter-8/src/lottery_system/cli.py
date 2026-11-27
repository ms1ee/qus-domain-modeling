"""Interactive command-line interface for the lottery system."""

from __future__ import annotations

from lottery_system.models import Prize, User, describe_prize_rules
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner


MENU_TEXT = """
==================== Team Building Lottery ====================
 1. Load built-in default participant list
 2. Upload custom participant list (txt)
 3. View department groups and member counts
 4. Load preset prize library
 5. Add custom prize
 6. Set avoidance groups for a prize
 7. Reorder prize sequence
 8. View prize configuration
 9. Start lottery
10. View winner list
11. Export winner list to txt (CSV format)
 0. Exit
==============================================================="""


def _ask(prompt: str) -> str:
    """Read a stripped line from stdin; exit cleanly on end of input."""
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        raise SystemExit(0)


def _ask_int(prompt: str, minimum: int = 1) -> int:
    """Prompt until the user enters an integer >= minimum."""
    while True:
        text = _ask(prompt)
        try:
            value = int(text)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if value < minimum:
            print(f"Please enter a number >= {minimum}.")
            continue
        return value


def _ordinal(number: int) -> str:
    """Format an integer as an English ordinal (1st, 2nd, 3rd, 4th...)."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _split_items(text: str) -> list[str]:
    """Split a comma-separated input into non-empty stripped items."""
    return [item.strip() for item in text.split(",") if item.strip()]


class LotterySystemCLI:
    """Drives the interactive lottery workflow."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.results = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ menu
    def run(self) -> None:
        """Main menu loop."""
        print("Welcome to the Company Team Building Smart Lottery System.")
        while True:
            print(MENU_TEXT)
            choice = _ask("Select an option: ")
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._upload_custom_list()
            elif choice == "3":
                self._view_groups()
            elif choice == "4":
                self._load_preset_prizes()
            elif choice == "5":
                self._add_custom_prize()
            elif choice == "6":
                self._set_avoid_groups()
            elif choice == "7":
                self._reorder_prizes()
            elif choice == "8":
                self._view_prizes()
            elif choice == "9":
                self._start_lottery()
            elif choice == "10":
                self._show_winners()
            elif choice == "11":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ----------------------------------------------------- list management
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._apply_loaded(users, errors, "built-in default list")

    def _upload_custom_list(self) -> None:
        path = _ask("Enter the path of the txt file (one 'Name,Department' per line): ")
        path = path.strip('"').strip("'")
        users, errors = self.list_manager.load_custom_list(path)
        self._apply_loaded(users, errors, f"file '{path}'")

    def _apply_loaded(self, users: list[User], errors: list[str], source: str) -> None:
        """Validate loaded users and let the operator decide on issues."""
        valid, duplicates = self.list_manager.validate_users(users)

        if not errors and not duplicates:
            if not valid:
                print(f"No valid participants found in {source}.")
                return
            self.users = valid
            print(f"Loaded {len(valid)} participants from {source}.")
            return

        print(
            f"Validation of {source} found {len(errors)} format error(s) "
            f"and {len(duplicates)} duplicate name(s):"
        )
        for error in errors:
            print("  " + error)
        for duplicate in duplicates:
            print(
                f"  Duplicate Name: {duplicate.name} ({duplicate.department}) "
                "- later entry ignored"
            )

        if not valid:
            print("No valid participants remain. Upload terminated.")
            return

        choice = _ask(
            "Remove invalid data and continue? [R]emove and continue / [T]erminate upload: "
        ).lower()
        if choice in ("r", "remove"):
            self.users = valid
            print(f"Loaded {len(valid)} valid participants from {source}.")
        else:
            print("Upload terminated. Participant list unchanged.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} member(s)")
        print(f"Total: {len(self.users)} participant(s) in {len(info)} group(s).")

    # ------------------------------------------------------ prize management
    def _load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print("  " + error)
        else:
            print("Preset prize library loaded.")

    def _add_custom_prize(self) -> None:
        name = _ask("Prize name: ")
        quantity = _ask_int("Quantity: ", minimum=1)
        if self.users:
            groups = sorted({user.department for user in self.users})
            print("Available groups: " + ", ".join(groups))
        avoid_text = _ask("Avoidance groups (comma-separated, blank for none): ")
        drawer = _ask("Associated lottery person (blank for none): ")
        try:
            prize = self.prize_manager.add_prize(
                name,
                quantity,
                avoid_groups=_split_items(avoid_text),
                associated_drawer=drawer or None,
            )
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prize_list(prizes)
        index = _ask_int("Select prize number: ", minimum=1)
        if index > len(prizes):
            print("Invalid prize number.")
            return
        prize = prizes[index - 1]
        if self.users:
            print("Available groups: " + ", ".join(sorted({u.department for u in self.users})))
        groups_text = _ask("Avoidance groups (comma-separated, blank to clear): ")
        if self.prize_manager.set_avoid_groups(prize.name, _split_items(groups_text)):
            print(f"Avoidance groups updated for '{prize.name}'.")
        else:
            print("Failed to update avoidance groups.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prize_list(prizes)
        text = _ask(
            "Enter new order as serial numbers (e.g. '2 1 3', blank to cancel): "
        )
        if not text:
            print("Reorder cancelled.")
            return
        try:
            order = [int(item) for item in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
            self._print_prize_list(self.prize_manager.get_prizes())
        else:
            print(
                f"Invalid order: provide each serial number from 1 to {len(prizes)} exactly once."
            )

    def _print_prize_list(self, prizes: list[Prize]) -> None:
        for position, prize in enumerate(prizes, start=1):
            print(f"  {position}. {prize.name} (quantity {prize.quantity})")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize configuration (lottery sequence):")
        for position, prize in enumerate(prizes, start=1):
            print(f"  {position}. {prize.name} - quantity {prize.quantity}")
            print(f"     Rule: {describe_prize_rules(prize)}")

    # ------------------------------------------------------------- lottery
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self.results.all_winners():
            confirm = _ask("Previous results will be discarded. Start a new lottery? (y/n): ")
            if confirm.lower() not in ("y", "yes"):
                print("Lottery cancelled.")
                return

        self.results = ResultManager()
        self.lottery = LotteryManager(self.users)
        print("\nLottery started. Commands: [Enter] = draw next, 'pause', 'terminate'.")

        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)

        print("\nAll lottery rounds completed.")
        self._print_summary(prizes)

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")

        self.lottery.begin_round(prize)
        print(f"Rule: {self.lottery.describe_rule(prize)}")

        round_winners: list[Winner] = []
        terminated = False

        while len(round_winners) < prize.quantity and not terminated:
            command = _ask("> ").lower()

            if command in ("terminate", "t"):
                terminated = True
                print("Round terminated by operator.")
                break

            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    paused_command = _ask("(paused) > ").lower()
                    if paused_command == "continue":
                        print("Lottery resumed.")
                        break
                    if paused_command in ("terminate", "t"):
                        terminated = True
                        print("Round terminated by operator.")
                        break
                    print("While paused, only 'continue' or 'terminate' is accepted.")
                continue

            if command == "continue":
                print("Lottery is not paused.")
                continue

            if command != "":
                print("Unknown command. Use [Enter], 'pause' or 'terminate'.")
                continue

            position = len(round_winners) + 1
            print(f"Currently drawing the {_ordinal(position)} winner...")
            user = self.lottery.draw_next(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends early.")
                break

            winner = self.results.add_winner(user, prize)
            round_winners.append(winner)
            print(
                f"Congratulations {user.name} ({user.department}) "
                f"for winning {prize.name}"
            )

        self.lottery.end_round(prize)

        print(f"\nRound {index} results ({len(round_winners)}/{prize.quantity} drawn):")
        if not round_winners:
            print("  No winners in this round.")
        for winner in round_winners:
            print(
                f"  {winner.winning_order}. {winner.user.name} "
                f"({winner.user.department}) - {winner.prize_name}"
            )

    def _print_summary(self, prizes: list[Prize]) -> None:
        grouped = self.results.get_winners_by_prize(prizes)
        print("\n==================== Complete Winner List ====================")
        if not any(grouped.values()):
            print("No winners were drawn.")
            return
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  - {winner.user.name} ({winner.user.department}) "
                    f"at {winner.winning_time:%Y-%m-%d %H:%M:%S}"
                )

    def _show_winners(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.results.all_winners():
            print("No winners recorded yet.")
            return
        self._print_summary(prizes)

    def _export_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        success, message = self.results.export_to_csv(prizes)
        print(message)


def main() -> None:
    """Application entry point."""
    try:
        LotterySystemCLI().run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
