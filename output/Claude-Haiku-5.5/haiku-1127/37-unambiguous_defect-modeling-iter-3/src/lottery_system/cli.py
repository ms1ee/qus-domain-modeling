"""Command-line interface for the team building lottery system."""
from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

SEPARATOR = "-" * 64


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def ask(prompt: str) -> str:
    """Read a stripped line from the user."""
    return input(prompt).strip()


class LotterySession:
    """Holds the state of one lottery event and drives the interactive menus."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.completed_prizes: set[str] = set()

    # ----- main loop ----------------------------------------------------
    def run(self) -> None:
        print("=" * 64)
        print("  Company Team Building Smart Lottery System")
        print("=" * 64)
        while True:
            print()
            print("1. Load participant list")
            print("2. View department groups")
            print("3. Configure prizes")
            print("4. Start lottery")
            print("5. View winner summary")
            print("6. Export results to file")
            print("0. Exit")
            choice = ask("Select an option: ")
            if choice == "1":
                self._load_participants()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._run_lottery()
            elif choice == "5":
                self._show_results()
            elif choice == "6":
                self._export()
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Invalid option, please try again.")

    # ----- list management ----------------------------------------------
    def _load_participants(self) -> None:
        print("Participant list source:")
        print("  1. Built-in default team building list")
        print("  2. Custom txt file (one 'Name,Department' per line)")
        choice = ask("Select source [1/2]: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            for error in errors:
                print(error)
        elif choice == "2":
            path = ask("Enter txt file path: ").strip('"').strip("'")
            users, errors = self.list_manager.load_custom_list(path)
            users = self._verify_custom_list(users, errors)
            if users is None:
                print("Upload terminated. Current list is unchanged.")
                return
        else:
            print("Invalid source selection.")
            return

        if not users:
            print("No valid participants loaded. Current list is unchanged.")
            return

        self.users = users
        self.lottery = LotteryManager(users)
        self.result_manager = ResultManager()
        self.completed_prizes = set()
        print(f"Loaded {len(users)} participants. Previous results (if any) were reset.")
        self._show_groups()

    def _verify_custom_list(
        self, users: list[User], errors: list[str]
    ) -> list[User] | None:
        """Detect duplicates/format errors and let the operator decide.

        Returns the list to use, or None if the upload is terminated.
        """
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            print(f"Verification passed: {len(valid)} participants.")
            return valid

        print("Verification found issues:")
        for error in errors:
            print(f"  {error}")
        for dup in duplicates:
            print(f"  Duplicate Name: '{dup.name}' ({dup.department})")

        print("Options:")
        print("  1. Remove invalid data (format errors and duplicates) and continue")
        print("  2. Remove specific entries by name and continue")
        print("  3. Terminate upload")
        choice = ask("Select option [1/2/3]: ")
        if choice == "1":
            return valid
        if choice == "2":
            names = ask("Enter names to remove (comma-separated): ")
            to_remove = {n.strip().casefold() for n in names.split(",") if n.strip()}
            remaining = [u for u in valid if u.name.strip().casefold() not in to_remove]
            removed = len(valid) - len(remaining)
            print(f"Removed {removed} entries.")
            return remaining
        return None

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in info.items():
            print(f"  {group}: {count} people")
        print(f"  Total: {sum(info.values())} people in {len(info)} groups")

    # ----- prize configuration ------------------------------------------
    def _prize_menu(self) -> None:
        while True:
            print()
            print("Prize configuration:")
            print("  1. Load preset prizes")
            print("  2. Add custom prize")
            print("  3. View prizes (lottery order)")
            print("  4. Reorder lottery sequence")
            print("  0. Back")
            choice = ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"Error: {error}")
                if not errors:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _add_prize(self) -> None:
        name = ask("Prize name: ")
        try:
            quantity = int(ask("Quantity: "))
        except ValueError:
            print("Error: quantity must be an integer.")
            return
        if self.users:
            info = self.list_manager.get_group_info(self.users)
            print("Available department groups: " + ", ".join(info.keys()))
        groups_text = ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [g.strip() for g in groups_text.split(",") if g.strip()]
        drawer = ask("Associated lottery person (blank for none): ")
        try:
            prize = self.prize_manager.add_prize(
                name, quantity, groups, drawer or None
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added at position {len(self.prize_manager.get_prizes())}: {prize.name}")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} | quantity: {prize.quantity}")
            print(f"     drawer: {prize.associated_drawer or 'None'}")
            print(f"     avoid groups: {', '.join(prize.avoid_groups) or 'None'}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = ask("Enter new order as serial numbers separated by spaces: ")
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            print("Error: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
        else:
            print(f"Error: order must contain each number 1-{len(prizes)} exactly once.")

    # ----- lottery process ----------------------------------------------
    def _run_lottery(self) -> None:
        if not self.users or self.lottery is None:
            print("Load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Configure at least one prize first.")
            return
        pending = [p for p in prizes if p.name not in self.completed_prizes]
        if not pending:
            print("All prizes have already been drawn.")
            return
        print(f"Starting lottery with {len(pending)} round(s).")
        for round_no, prize in enumerate(prizes, start=1):
            if prize.name in self.completed_prizes:
                continue
            self._run_round(round_no, prize)
        print()
        print("Lottery finished. Winner summary:")
        self._show_results()

    def _run_round(self, round_no: int, prize: Prize) -> None:
        assert self.lottery is not None
        print()
        print(SEPARATOR)
        print(f"Round {round_no}: {prize.name}")
        print(f"Quantity: {prize.quantity} | Drawer: {prize.associated_drawer or 'None'}")
        print(f"Rule: {self.lottery.describe_rule(prize)}")
        print(SEPARATOR)

        round_winners: list[Winner] = []
        drawn = 0
        while drawn < prize.quantity:
            command = ask(
                f"[Enter] draw the {ordinal(drawn + 1)} winner | "
                "'pause' | 'terminate': "
            ).casefold()
            if command == "terminate":
                print("Round terminated by operator. Remaining winners skipped.")
                break
            if command == "pause":
                if not self._pause_round():
                    print("Round terminated by operator. Remaining winners skipped.")
                    break
            elif command:
                print(f"Unknown command '{command}'.")
                continue

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = self.lottery.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            drawn += 1
            round_winners.append(winner)
            print(
                f"Congratulations {user.name} ({user.department}) "
                f"for winning {prize.name}!"
            )

        self.completed_prizes.add(prize.name)
        print()
        print(f"Round {round_no} results ({len(round_winners)} winner(s)):")
        if not round_winners:
            print("  (none)")
        for winner in round_winners:
            print(f"  {winner.winning_order}. {winner.name} ({winner.department})")

    def _pause_round(self) -> bool:
        """Pause the lottery. Returns True to resume, False to terminate the round."""
        print("Lottery paused.")
        while True:
            command = ask("Type 'continue' to resume or 'terminate' to end this round: ")
            command = command.casefold()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Unknown command.")

    # ----- results ------------------------------------------------------
    def _show_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            print("No winners yet.")
            return
        print(SEPARATOR)
        print("Winner list (by prize level, then winning order):")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"{prize_name}:")
            for winner in winners:
                print(
                    f"  {winner.winning_order:>3}. {winner.name} "
                    f"({winner.department})"
                )
        print(SEPARATOR)

    def _export(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not any(self.result_manager.get_winners_by_prize(prizes).values()):
            print("No winners to export.")
            return
        _, message = self.result_manager.export_to_csv(prizes)
        print(message)


def main() -> int:
    """Entry point for the interactive program."""
    session = LotterySession()
    try:
        session.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
    return 0
