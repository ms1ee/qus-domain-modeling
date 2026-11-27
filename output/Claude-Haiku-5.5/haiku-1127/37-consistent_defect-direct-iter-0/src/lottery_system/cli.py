"""Command-line interaction for the team building lottery system."""

from __future__ import annotations

import re

from lottery_system.models import DRAWER_CHOICES, Prize, User, normalize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive controller for the whole lottery process."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ----- basic helpers -------------------------------------------------

    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def run(self) -> int:
        self._banner()

        users = self._load_participants()
        if not users:
            print("No participants loaded. Exiting.")
            return 0
        self.users = users

        if not self._configure_prizes():
            print("Exiting without starting the lottery.")
            return 0

        self.lottery = LotteryManager(self.users)
        self._run_lottery()
        self._show_summary()
        self._offer_export()
        print("\nThank you for using the Smart Lottery System.")
        return 0

    @staticmethod
    def _banner() -> None:
        print("=" * 60)
        print("  Company Team Building Event - Smart Lottery System")
        print("=" * 60)

    # ----- step 1: participant list -------------------------------------

    def _load_participants(self) -> list[User] | None:
        while True:
            print("\n=== Step 1: Load Participant List ===")
            print("1. Load built-in default list")
            print("2. Upload custom txt list (format: Name,Department Group)")
            print("0. Quit")
            choice = self._ask("Select an option: ")

            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self._ask("Enter the txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
            elif choice == "0":
                return None
            else:
                print("Invalid option, please try again.")
                continue

            if not users:
                self._print_problems(errors, [])
                print("No valid participants found, please try again.")
                continue

            verified = self._verify_users(users, errors)
            if not verified:
                continue

            self._print_groups(verified)
            return verified

    def _verify_users(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Detect duplicates and format errors; let the operator decide."""
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            return valid

        self._print_problems(errors, duplicates)
        while True:
            print("\nOptions:")
            print("  r - remove all invalid data and continue")
            print("  n - remove specific names manually and continue")
            print("  t - terminate the upload")
            action = self._ask("Select an action: ").lower()

            if action == "r":
                return valid
            if action == "n":
                raw = self._ask("Enter names to remove (comma separated): ")
                remove_keys = {normalize(n) for n in raw.split(",") if n.strip()}
                remaining = [u for u in valid if normalize(u.name) not in remove_keys]
                removed = len(valid) - len(remaining)
                print(f"Removed {removed} participant(s).")
                return remaining
            if action == "t":
                print("Upload terminated.")
                return None
            print("Unknown action, please choose r, n or t.")

    @staticmethod
    def _print_problems(errors: list[str], duplicates: list[User]) -> None:
        if errors:
            print(f"\nFound {len(errors)} format error(s):")
            for error in errors:
                print(f"  - {error}")
        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  - Duplicate Name: {user.name} ({user.department})")

    def _print_groups(self, users: list[User]) -> None:
        info = self.list_manager.get_group_info(users)
        print(f"\nValid department groups ({len(info)}):")
        for department, count in info.items():
            print(f"  - {department}: {count} people")
        print(f"Total participants: {len(users)}")

    # ----- step 2: prize configuration ----------------------------------

    def _configure_prizes(self) -> bool:
        """Prize configuration menu. Returns True when the lottery should start."""
        while True:
            print("\n=== Step 2: Prize Configuration ===")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prize list and rule settings")
            print("4. Adjust lottery sequence")
            print("5. View participant groups")
            print("6. Start lottery")
            print("0. Quit")
            choice = self._ask("Select an option: ")

            if choice == "1":
                for error in self.prize_manager.load_default_prizes():
                    print(error)
                print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._print_groups(self.users)
            elif choice == "6":
                if not self.prize_manager.get_prizes():
                    print("Please configure at least one prize first.")
                    continue
                return True
            elif choice == "0":
                return False
            else:
                print("Invalid option, please try again.")

    def _group_names(self) -> list[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self._ask_drawer()
        groups = self._ask_avoid_groups()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            text = self._ask(prompt)
            if text.isdigit() and int(text) > 0:
                return int(text)
            print("Please enter a positive whole number.")

    def _ask_drawer(self) -> str | None:
        print("Associated lottery person (optional):")
        for index, person in enumerate(DRAWER_CHOICES, start=1):
            print(f"  {index}. {person}")
        print("  Enter a number, type another name, or press Enter for none.")
        text = self._ask("Choice: ")
        if not text:
            return None
        if text.isdigit() and 1 <= int(text) <= len(DRAWER_CHOICES):
            return DRAWER_CHOICES[int(text) - 1]
        return text

    def _ask_avoid_groups(self) -> list[str]:
        groups = self._group_names()
        if not groups:
            return []
        print("Department groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        text = self._ask(
            "Avoid group numbers or names (comma separated, Enter for none): "
        )
        selected: list[str] = []
        for token in (t.strip() for t in text.split(",")):
            if not token:
                continue
            match: str | None
            if token.isdigit() and 1 <= int(token) <= len(groups):
                match = groups[int(token) - 1]
            else:
                match = next((g for g in groups if normalize(g) == normalize(token)), None)
            if match is None:
                print(f"Unknown group ignored: {token}")
            elif match not in selected:
                selected.append(match)
        return selected

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            self._print_prize_line(index, prize)

    @staticmethod
    def _print_prize_line(index: int, prize: Prize) -> None:
        drawer = prize.associated_drawer or "None"
        groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        print(
            f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
            f"Lottery person: {drawer} | Avoid groups: {groups}"
        )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes to reorder.")
            return
        self._view_prizes()
        print("Enter the new order as serial numbers (e.g. '2 1 3' or '2,1,3').")
        text = self._ask("New order (Enter to cancel): ")
        if not text:
            print("Reorder cancelled.")
            return
        tokens = [t for t in re.split(r"[\s,]+", text) if t]
        try:
            order = [int(t) for t in tokens]
        except ValueError:
            print("Invalid input: please enter numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- step 3: lottery ----------------------------------------------

    def _run_lottery(self) -> None:
        assert self.lottery is not None
        prizes = self.prize_manager.get_prizes()
        print("\n=== Step 3: Lottery ===")
        print("Before each draw: press Enter to draw, 'pause' to interrupt,")
        print("or 'terminate' to end the current round and skip it.")

        for round_no, prize in enumerate(prizes, start=1):
            print(f"\n===== Round {round_no}: {prize.name} =====")
            print(f"Quantity: {prize.quantity}")
            print(f"Rule: {self.lottery.describe_rule(prize)}")
            self.lottery.start_round(prize)

            round_winners = []
            for position in range(1, prize.quantity + 1):
                command = self._wait_for_command()
                if command == "terminate":
                    print("Round terminated; remaining draws are skipped.")
                    break
                print(f"Currently drawing the {_ordinal(position)} winner...")
                winner = self.lottery.draw_one(prize)
                if winner is None:
                    print("No eligible candidates remain for this prize.")
                    break
                round_winners.append(winner)
                user = winner.user
                print(
                    f"Congratulations {user.name} ({user.department}) "
                    f"for winning {prize.name}!"
                )

            print(f"\n--- Round {round_no} results ({len(round_winners)} winner(s)) ---")
            for winner in round_winners:
                print(
                    f"  {_ordinal(winner.sequence)} overall: {winner.user.name} "
                    f"({winner.user.department})"
                )

    def _wait_for_command(self) -> str:
        """Return 'draw' or 'terminate'. Handles 'pause' / 'continue'."""
        while True:
            command = self._ask(
                "Press Enter to draw next winner (pause / terminate): "
            ).lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to skip.")
                while True:
                    resume = self._ask("> ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        break
                    if resume == "terminate":
                        return "terminate"
                    print("Please type 'continue' or 'terminate'.")
                continue
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # ----- step 4: results ----------------------------------------------

    def _show_summary(self) -> None:
        assert self.lottery is not None
        prizes = self.prize_manager.get_prizes()
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        print("\n=== Final Winner List (by prize level, high to low) ===")
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.sequence}. {winner.user.name} "
                    f"({winner.user.department}) - {winner.winning_time}"
                )

    def _offer_export(self) -> None:
        assert self.lottery is not None
        answer = self._ask("\nExport the winner list to a file? (y/n): ").lower()
        if answer in ("y", "yes"):
            _, message = self.lottery.result_manager.export_to_csv(
                self.prize_manager.get_prizes()
            )
            print(message)


def main() -> int:
    """Run the interactive lottery system."""
    try:
        return LotterySystemCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nSession ended.")
        return 1
