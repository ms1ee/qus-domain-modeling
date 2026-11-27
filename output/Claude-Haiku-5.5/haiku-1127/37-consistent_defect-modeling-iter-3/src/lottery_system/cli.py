"""Command-line interaction for the team building lottery."""

from __future__ import annotations

import re

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAWER_OPTIONS: list[str] = ["Chen Qixian", "Jin Duo", "Ma Jiaqi", "Li Bin"]
SEPARATOR = "-" * 64


def ordinal(number: int) -> str:
    """Return 1 -> '1st', 2 -> '2nd', 11 -> '11th', etc."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def ask(prompt: str) -> str:
    return input(prompt)


def ask_int(prompt: str, minimum: int = 1) -> int:
    while True:
        text = ask(prompt).strip()
        try:
            value = int(text)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value < minimum:
            print(f"Please enter a number >= {minimum}.")
            continue
        return value


def ask_yes_no(prompt: str) -> bool:
    return ask(prompt).strip().lower() in ("y", "yes")


def parse_int_list(text: str) -> list[int]:
    """Parse '2 1 3' or '2,1,3' into [2, 1, 3]. Raises ValueError on bad input."""
    tokens = [token for token in re.split(r"[,\s]+", text.strip()) if token]
    return [int(token) for token in tokens]


class LotteryCLI:
    """Interactive controller for the whole lottery process."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.results = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ flow
    def run(self) -> None:
        print(SEPARATOR)
        print("  Company Team Building - Smart Lottery System")
        print(SEPARATOR)

        self.users = self.setup_participants()
        if not self.users:
            print("No participants loaded. Exiting.")
            return

        self.setup_prizes()
        self.lottery = LotteryManager(self.users)
        self.run_lottery()
        self.show_summary()
        self.export_results()
        print("Thank you for using the lottery system.")

    # ----------------------------------------------------------- participants
    def setup_participants(self) -> list[User]:
        while True:
            print("\nSelect participant list source:")
            print("  1. Built-in team building list")
            print("  2. Upload custom txt list (format: Name,Department or Name;Department)")
            print("  0. Exit")
            choice = ask("Select an option: ").strip()

            if choice == "0":
                return []
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = ask("Enter the txt file path: ").strip()
                users, errors = self.list_manager.load_custom_list(path)
            else:
                print("Invalid option.")
                continue

            reviewed = self.review_list(users, errors)
            if reviewed is None:
                print("Upload terminated. Returning to source selection.")
                continue
            if not reviewed:
                print("No valid participants found.")
                continue

            self.print_group_info(reviewed)
            return reviewed

    def review_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Verify the list. Returns cleaned users, or None if the upload is terminated."""
        if errors:
            print(f"\nFound {len(errors)} invalid entr{'y' if len(errors) == 1 else 'ies'}:")
            for error in errors:
                print(f"  {error}")
            print("  1. Remove invalid data and continue")
            print("  2. Terminate upload")
            if ask("Choose an option: ").strip() != "1":
                return None

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  Duplicate: {user.name} ({user.department})")
            print("  1. Remove duplicates (keep first occurrence) and continue")
            print("  2. Terminate upload")
            if ask("Choose an option: ").strip() != "1":
                return None
        return valid

    def print_group_info(self, users: list[User]) -> None:
        info = self.list_manager.get_group_info(users)
        print(f"\nLoaded {len(users)} participant(s) in {len(info)} group(s):")
        for group, count in info.items():
            print(f"  {group}: {count}")

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    # ----------------------------------------------------------------- prizes
    def setup_prizes(self) -> None:
        while True:
            print("\nPrize configuration:")
            print("  1. Load preset prize library")
            print("  2. Add custom prize")
            print("  3. Configure avoidance groups / lottery person for a prize")
            print("  4. Reorder prizes (lottery sequence)")
            print("  5. Show prizes")
            print("  0. Finish configuration and continue")
            choice = ask("Select an option: ").strip()

            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  Skipped: {error}")
                print("Preset prizes loaded.")
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.configure_prize()
            elif choice == "4":
                self.reorder_prizes_cli()
            elif choice == "5":
                self.show_prizes()
            elif choice == "0":
                if not self.prize_manager.get_prizes():
                    print("Please add at least one prize before starting.")
                    continue
                self.show_prizes()
                return
            else:
                print("Invalid option.")

    def add_custom_prize(self) -> None:
        name = ask("Prize name: ").strip()
        if not name:
            print("Prize name must not be empty.")
            return
        quantity = ask_int("Prize quantity: ")
        groups = self._choose_groups()
        drawer = self._choose_drawer()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize added: {prize.name} (quantity {prize.quantity}).")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_prize(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes to configure.")
            return
        self.show_prizes()
        index = ask_int("Enter the serial number of the prize to configure: ")
        if index > len(prizes):
            print("Serial number out of range.")
            return
        prize = prizes[index - 1]
        prize.avoid_groups = self._choose_groups()
        prize.associated_drawer = self._choose_drawer()
        print(f"Updated rules for: {prize.name}")

    def reorder_prizes_cli(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes to reorder.")
            return
        self.show_prizes()
        text = ask("Enter the new order as serial numbers (e.g. 2 1 3): ")
        try:
            order = parse_int_list(text)
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self.show_prizes()
        else:
            print("Invalid order: each current serial number must appear exactly once.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("  (no prizes configured)")
            return
        print("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {groups}"
            )

    def _choose_groups(self) -> list[str]:
        groups = self._group_names()
        if not groups:
            return []
        print("Available department groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        while True:
            text = ask("Select avoidance group numbers, comma-separated (blank for none): ").strip()
            if not text:
                return []
            try:
                indexes = parse_int_list(text)
            except ValueError:
                print("Please enter group numbers only.")
                continue
            if any(i < 1 or i > len(groups) for i in indexes):
                print("One or more group numbers are out of range.")
                continue
            selected: list[str] = []
            for i in indexes:
                if groups[i - 1] not in selected:
                    selected.append(groups[i - 1])
            return selected

    def _choose_drawer(self) -> str | None:
        print("Lottery person:")
        print("  0. None")
        for index, name in enumerate(DRAWER_OPTIONS, start=1):
            print(f"  {index}. {name}")
        print(f"  {len(DRAWER_OPTIONS) + 1}. Other (type a name)")
        while True:
            choice = ask("Select a lottery person: ").strip()
            if choice == "0":
                return None
            if choice.isdigit():
                number = int(choice)
                if 1 <= number <= len(DRAWER_OPTIONS):
                    return DRAWER_OPTIONS[number - 1]
                if number == len(DRAWER_OPTIONS) + 1:
                    custom = ask("Enter the lottery person's name: ").strip()
                    return custom or None
            print("Invalid selection.")

    # ---------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        assert self.lottery is not None
        prizes = self.prize_manager.get_prizes()
        print(SEPARATOR)
        print("Lottery starts!")
        print("Commands: Enter or 'continue' = next draw | 'pause' = pause | "
              "'terminate' = end current round")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, prize)
        print(SEPARATOR)
        print("All lottery rounds completed.")

    def _run_round(self, round_no: int, prize) -> None:
        assert self.lottery is not None
        print(SEPARATOR)
        print(f"Round {round_no}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self.lottery.describe_rule(prize)}")

        round_winners: list[User] = []
        while len(round_winners) < prize.quantity:
            command = ask("Press Enter to draw (or 'pause' / 'terminate'): ").strip().lower()
            if command == "terminate":
                print("Current round terminated.")
                break
            if command == "pause":
                self.lottery.status = "paused"
                if self._handle_pause():
                    print("Current round terminated.")
                    break
                self.lottery.status = "running"
            elif command not in ("", "continue"):
                print("Unknown command.")
                continue

            position = len(round_winners) + 1
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize.")
                break
            self.results.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.lottery.finish_round(prize, round_winners)
        self.lottery.status = "idle"

        if round_winners:
            print(f"Round {round_no} results:")
            for position, user in enumerate(round_winners, start=1):
                print(f"  {position}. {user.name} ({user.department})")
        else:
            print("No winners were drawn in this round.")
        if len(round_winners) < prize.quantity:
            print(f"Note: {len(round_winners)} of {prize.quantity} prize(s) awarded.")

    def _handle_pause(self) -> bool:
        """Wait until 'continue' (returns False) or 'terminate' (returns True)."""
        print("Lottery paused.")
        while True:
            command = ask("Type 'continue' to resume or 'terminate' to end this round: ")
            command = command.strip().lower()
            if command in ("continue", ""):
                print("Lottery resumed.")
                return False
            if command == "terminate":
                return True
            print("Unknown command.")

    # ---------------------------------------------------------------- results
    def show_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        by_prize = self.results.get_winners_by_prize(prizes)
        print(SEPARATOR)
        print("FINAL WINNER LIST (by prize level, high to low)")
        print(SEPARATOR)
        if not any(by_prize.values()):
            print("No winners.")
            return
        for prize in sorted(prizes, key=lambda p: p.level):
            winners = by_prize[prize.name]
            if not winners:
                continue
            print(f"{prize.name}:")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.user.name} "
                    f"({winner.user.department}) - {prize.name}"
                )

    def export_results(self) -> None:
        if not ask_yes_no("Export the winner list to file? (y/n): "):
            return
        _, message = self.results.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    try:
        LotteryCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExited.")


if __name__ == "__main__":
    main()
