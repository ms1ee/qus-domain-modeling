"""Command-line interface for the lottery system."""

import re
import time

from lottery_system.constants import CHENG_RU_GROUP, LI_BIN
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import sort_prizes_by_level

DRAW_DELAY_SECONDS = 0.8


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _same_text(a: str | None, b: str) -> bool:
    return a is not None and a.strip().casefold() == b.casefold()


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            raw = self._ask(prompt)
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            print("Please enter a positive integer.")

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("=" * 60)
        print("Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ")
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.show_results(ask_export=True)
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid option, please try again.")

    @staticmethod
    def _print_main_menu() -> None:
        print("\n---------------- Main Menu ----------------")
        print("1. Load participant list")
        print("2. View department groups")
        print("3. Prize configuration")
        print("4. Start lottery")
        print("5. View / export results")
        print("0. Exit")

    # ------------------------------------------------------- list management
    def load_participants(self) -> None:
        print("\n-- Load participant list --")
        print("1. Built-in default team building list")
        print("2. Custom txt list (format: Name,Department per line)")
        print("0. Cancel")
        choice = self._ask("Select an option: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip('"').strip("'")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return
        self._verify_and_apply_list(users, errors)

    def _verify_and_apply_list(self, users: list[User], errors: list[str]) -> None:
        if errors:
            print("Format errors detected:")
            for error in errors:
                print(f"  {error}")
            choice = self._ask(
                "Enter 'r' to remove invalid data and continue, 't' to terminate upload: "
            ).lower()
            if choice != "r":
                print("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print("Duplicate names detected (later occurrences):")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            choice = self._ask(
                "Enter 'r' to remove duplicates and continue, 't' to terminate upload: "
            ).lower()
            if choice != "r":
                print("Upload terminated.")
                return

        if not valid:
            print("No valid participants found. Upload cancelled.")
            return

        self.users = valid
        self.lottery = None
        print(f"Loaded {len(valid)} valid participant(s).")
        self.show_groups()

    def show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nDepartment groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} people")

    # --------------------------------------------------------- prize config
    def prize_menu(self) -> None:
        while True:
            print("\n-- Prize configuration --")
            print("1. Load preset prizes")
            print("2. View prizes")
            print("3. Add custom prize")
            print("4. Reorder lottery sequence")
            print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  {error}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._print_prizes(self.prize_manager.get_prizes())
            elif choice == "3":
                self.add_prize_interactive()
            elif choice == "4":
                self.reorder_prizes_interactive()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _print_prizes(self, prizes: list[Prize]) -> None:
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {avoid}"
            )

    def add_prize_interactive(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_positive_int("Quantity: ")
        avoid_groups = self._select_avoid_groups()
        drawer = self._ask("Associated lottery person (press Enter for none): ") or None
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
            print(f"Prize '{name.strip()}' added.")
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")

    def _select_avoid_groups(self) -> list[str]:
        if not self.users:
            print("No participant list loaded; no avoidance groups can be selected.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        print("Available groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        raw = self._ask("Enter group numbers to avoid, comma separated (Enter for none): ")
        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            group = None
            if token.isdigit() and 1 <= int(token) <= len(groups):
                group = groups[int(token) - 1]
            else:
                for candidate in groups:
                    if candidate.casefold() == token.casefold():
                        group = candidate
                        break
            if group is None:
                print(f"  Ignored unknown group: '{token}'")
            elif group not in selected:
                selected.append(group)
        return selected

    def reorder_prizes_interactive(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes(prizes)
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._print_prizes(self.prize_manager.get_prizes())
        else:
            print(f"Invalid order: each serial number 1-{len(prizes)} must appear exactly once.")

    # ------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is not None and self.lottery.result_manager.get_all_winners():
            confirm = self._ask("Existing results will be cleared. Start a new lottery? (y/n): ")
            if confirm.lower() != "y":
                return

        self.lottery = LotteryManager(self.users)
        total_rounds = len(prizes)
        print(f"\nLottery started: {total_rounds} round(s).")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, total_rounds, prize)
        print("\nAll lottery rounds completed.")
        self.show_results(ask_export=False)

    def _describe_rule(self, prize: Prize) -> str:
        rules: list[str] = []
        if _same_text(prize.associated_drawer, LI_BIN):
            rules.append("Relaxed rules: previous winners excluded, avoidance groups ignored")
        else:
            rules.append("Previous winners excluded")
            if prize.avoid_groups:
                rules.append("Avoid groups: " + ", ".join(prize.avoid_groups))
        if self.lottery is not None and self.lottery.is_fallback_for(prize):
            rules.append(f"Cheng Ru group protection: only {CHENG_RU_GROUP} members eligible")
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        return "; ".join(rules)

    def _run_round(self, round_no: int, total_rounds: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {round_no}/{total_rounds}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._describe_rule(prize)}")
        print("Commands: Enter = draw next | pause | terminate")

        round_winners: list[User] = []
        while len(round_winners) < prize.quantity:
            command = self._ask("> ").lower()
            if command == "terminate":
                print("Round terminated; remaining winners skipped.")
                break
            if command == "pause":
                if not self._wait_while_paused():
                    print("Round terminated; remaining winners skipped.")
                    break
            elif command not in ("", "continue"):
                print("Unknown command. Use Enter, 'pause' or 'terminate'.")
                continue

            position = len(round_winners) + 1
            print(f"Currently drawing the {_ordinal(position)} winner...")
            time.sleep(DRAW_DELAY_SECONDS)
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize; round ends early.")
                break
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.lottery.record_round_result(prize, round_winners)

        print(f"\nRound result for {prize.name} (winning order):")
        if not round_winners:
            print("  (no winners)")
        for order, user in enumerate(round_winners, start=1):
            print(f"  {order}. {user.name} ({user.department})")

    @staticmethod
    def _wait_while_paused() -> bool:
        """Block until 'continue' (returns True) or 'terminate' (returns False)."""
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = input("(paused) > ").strip().lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Unknown command. Use 'continue' or 'terminate'.")

    # ------------------------------------------------------------- results
    def show_results(self, ask_export: bool = True) -> None:
        if self.lottery is None or not self.lottery.result_manager.get_all_winners():
            print("No lottery results yet.")
            return
        prizes = sort_prizes_by_level(self.prize_manager.get_prizes())
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)

        print("\n==================== Winner List ====================")
        for prize in prizes:
            print(f"\n[{prize.name}]")
            winners = grouped.get(prize.name, [])
            if not winners:
                print("  (no winners)")
            for order, winner in enumerate(winners, start=1):
                print(f"  {order}. {winner.user.name} ({winner.user.department})")

        if ask_export:
            choice = self._ask("\nExport results to txt (CSV format)? (y/n): ")
            if choice.lower() == "y":
                _, message = self.lottery.result_manager.export_to_csv(prizes)
                print(message)


def main() -> None:
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
