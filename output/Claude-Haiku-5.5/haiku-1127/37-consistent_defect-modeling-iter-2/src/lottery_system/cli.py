"""Command-line interface for the team building lottery system."""

from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

LOTTERY_PERSONS = ["Chen Qixian", "Jin Duo", "Ma Jiaqi", "Li Bin"]
SEPARATOR = "=" * 64


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer (e.g. 1st, 12th)."""
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryApp:
    """Interactive console application."""

    def __init__(self) -> None:
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._result_manager = ResultManager()
        self._users: list[User] = []

    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def run(self) -> None:
        print(SEPARATOR)
        print("  Company Team Building - Smart Lottery System")
        print(SEPARATOR)
        actions = {
            "1": self._load_participants,
            "2": self._show_groups,
            "3": self._configure_prizes,
            "4": self._start_lottery,
            "5": self._show_results,
        }
        while True:
            print("\nMain Menu")
            print("1. Load participant list")
            print("2. View department groups")
            print("3. Configure prizes")
            print("4. Start lottery")
            print("5. View / export results")
            print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid option, please try again.")
            else:
                action()

    # ------------------------------------------------------------------ list

    def _load_participants(self) -> None:
        print("\nParticipant list source:")
        print("1. Built-in default team building list")
        print("2. Custom txt file (each line: Name,Department Group)")
        print("0. Back")
        choice = self._ask("Select an option: ")
        if choice == "1":
            users, errors = self._list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter path to txt file: ")
            users, errors = self._list_manager.load_custom_list(path)
        else:
            return

        accepted = self._verify_participants(users, errors)
        if accepted is None:
            print("Participant list was not loaded.")
            return
        self._users = accepted
        self._result_manager = ResultManager()
        print(f"Loaded {len(accepted)} participants. Previous results (if any) were cleared.")
        self._show_groups()

    def _verify_participants(self, users: list[User], errors: list[str]) -> list[User] | None:
        if errors:
            print("\nFormat errors found:")
            for error in errors:
                print(f"  - {error}")

        valid, duplicates = self._list_manager.validate_users(users)
        if duplicates:
            print("\nDuplicate names found (later occurrences are invalid):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")

        if not errors and not duplicates:
            return valid

        print(f"\nValid records: {len(valid)}")
        while True:
            decision = self._ask(
                "Type 'remove' to discard invalid data and continue, "
                "or 'terminate' to abort the upload: "
            ).lower()
            if decision == "remove":
                if not valid:
                    print("No valid participants remain; upload aborted.")
                    return None
                print(f"Removed {len(errors) + len(duplicates)} invalid record(s).")
                return valid
            if decision == "terminate":
                print("Upload terminated.")
                return None
            print("Please type 'remove' or 'terminate'.")

    def _show_groups(self) -> None:
        if not self._users:
            print("No participant list loaded.")
            return
        info = self._list_manager.get_group_info(self._users)
        print("\nDepartment groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self._users)} people")

    # ---------------------------------------------------------------- prizes

    def _configure_prizes(self) -> None:
        while True:
            print("\nPrize Configuration")
            print("1. Load preset prizes")
            print("2. Add custom prize")
            print("3. View prize list")
            print("4. Reorder lottery sequence")
            print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self._prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  - {error}")
                if not errors:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _view_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "None"
            avoid = ", ".join(prize.avoid_groups) or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} "
                f"| Lottery person: {drawer} | Avoid groups: {avoid}"
            )

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity_text = self._ask("Quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            print("Quantity must be a positive integer.")
            return
        groups_text = self._ask("Avoidance groups (comma-separated department names, blank for none): ")
        avoid = [group.strip() for group in groups_text.split(",") if group.strip()]
        drawer = self._ask(f"Associated lottery person ({', '.join(LOTTERY_PERSONS)}, blank for none): ")
        try:
            prize = self._prize_manager.add_prize(name, int(quantity_text), avoid, drawer or None)
        except ValueError as exc:
            print(f"Could not add prize: {exc}")
            return
        print(f"Prize added: {prize.name}")

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(item) for item in text.split()]
        except ValueError:
            print("Invalid input: please enter integers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._view_prizes()
        else:
            print("Invalid order: every current serial number must appear exactly once.")

    # ---------------------------------------------------------------- lottery

    def _start_lottery(self) -> None:
        if not self._users:
            print("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        if self._result_manager.get_all_winners():
            confirm = self._ask("Existing results will be discarded. Start a new lottery? (y/n): ").lower()
            if confirm != "y":
                return
            self._result_manager = ResultManager()

        lottery = LotteryManager(self._users)
        total = len(prizes)
        print("\nLottery started!")
        for number, prize in enumerate(prizes, start=1):
            self._run_round(number, total, prize, lottery)

        print(f"\n{SEPARATOR}\nLottery finished!")
        self._print_summary(prizes)
        if self._ask("Export results to file? (y/n): ").lower() == "y":
            self._export(prizes)

    def _run_round(self, number: int, total: int, prize: Prize, lottery: LotteryManager) -> None:
        print(f"\n--- Round {number}/{total}: {prize.name} ---")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        drawn: list[Winner] = []
        while len(drawn) < prize.quantity:
            command = self._ask("Press Enter to draw (or 'pause' / 'terminate'): ").lower()
            if command == "pause":
                if not self._handle_pause():
                    break
                continue
            if command == "terminate":
                print("Round terminated, skipping remaining draws.")
                break
            if command not in ("", "draw"):
                print("Unknown command.")
                continue

            user = lottery.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize; round ends.")
                break
            winner = self._result_manager.add_winner(user, prize)
            drawn.append(winner)
            print(f"Currently drawing the {ordinal(len(drawn))} winner...")
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"Round {number} finished with {len(drawn)} winner(s).")
        for winner in drawn:
            print(f"  {winner.winning_order}. {winner.user.name} ({winner.user.department})")

    def _handle_pause(self) -> bool:
        """Block until 'continue' (returns True) or 'terminate' (returns False)."""
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._ask("(paused) > ").lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                print("Round terminated, skipping remaining draws.")
                return False
            print("Unknown command. Type 'continue' or 'terminate'.")

    # ---------------------------------------------------------------- results

    def _print_summary(self, prizes: list[Prize]) -> None:
        winners = self._result_manager.get_winners_by_prize(prizes)
        print("\nFinal winner list (prize level from high to low):")
        for prize in sorted(prizes, key=lambda item: item.level):
            print(f"\n{prize.name} (quantity {prize.quantity})")
            entries = winners.get(prize.name, [])
            if not entries:
                print("  No winners")
                continue
            for winner in entries:
                print(
                    f"  {winner.winning_order}. {winner.user.name} "
                    f"({winner.user.department}) - {prize.name}"
                )

    def _export(self, prizes: list[Prize]) -> None:
        _, message = self._result_manager.export_to_csv(prizes)[0], self._result_manager.export_to_csv(prizes)[1]
        print(message)

    def _show_results(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not self._result_manager.get_all_winners():
            print("No results yet.")
            return
        self._print_summary(prizes)
        if self._ask("Export results to file? (y/n): ").lower() == "y":
            self._export(prizes)


def main() -> None:
    try:
        LotteryApp().run()
    except (EOFError, KeyboardInterrupt):
        print("\nProgram terminated.")
