"""Command-line interaction for the lottery process."""

from __future__ import annotations

import time

from lottery_system.constants import DRAW_DELAY_SECONDS
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.process_control import END_OF_INPUT, NO_INPUT, InputChannel


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryApp:
    """Interactive command-line application."""

    def __init__(self, channel: InputChannel | None = None) -> None:
        self.channel = channel if channel is not None else InputChannel()
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ----- main loop -----------------------------------------------------

    def run(self) -> None:
        print("=" * 60)
        print("Company Team Building - Smart Lottery System")
        print("=" * 60)
        try:
            while True:
                self._print_main_menu()
                choice = self._ask("Select an option: ").strip()
                if choice == "1":
                    self._load_participants()
                elif choice == "2":
                    self._show_groups()
                elif choice == "3":
                    self._configure_prizes()
                elif choice == "4":
                    self._run_lottery()
                elif choice == "5":
                    self._show_results()
                elif choice == "6":
                    self._export_results()
                elif choice == "0":
                    print("Goodbye!")
                    break
                else:
                    print("Invalid option, please try again.")
        except EOFError:
            print("\nInput closed. Exiting.")
        except KeyboardInterrupt:
            print("\nExiting.")

    @staticmethod
    def _print_main_menu() -> None:
        print("\n--- Main Menu ---")
        print("1. Load participant list")
        print("2. View department groups")
        print("3. Configure prizes")
        print("4. Start lottery")
        print("5. View results")
        print("6. Export results")
        print("0. Exit")

    def _ask(self, prompt: str) -> str:
        print(prompt, end="", flush=True)
        item = self.channel.get()
        if item is END_OF_INPUT:
            raise EOFError
        return item

    # ----- participant list ----------------------------------------------

    def _load_participants(self) -> None:
        print("1. Built-in default team building list")
        print("2. Custom txt list (format: Name,Department Group)")
        choice = self._ask("Choose a source: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid choice.")
            return

        for error in errors:
            print(error)
        valid, duplicates = self.list_manager.validate_users(users)
        for duplicate in duplicates:
            print(
                f"Duplicate Name: '{duplicate.name}' ({duplicate.department}) "
                f"appears more than once and was ignored."
            )

        if errors or duplicates:
            print(f"Found {len(errors)} format error(s) and {len(duplicates)} duplicate(s).")
            action = self._ask(
                "Enter 'r' to remove invalid data and continue, or 't' to terminate the upload: "
            ).strip().lower()
            if action != "r":
                print("Upload terminated. Participant list unchanged.")
                return

        if not valid:
            print("No valid participants loaded. Participant list unchanged.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} participants.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} member(s)")

    # ----- prize configuration -------------------------------------------

    def _configure_prizes(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes")
            print("4. Reorder lottery sequence")
            print("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"Error: {error}")
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
                print("Invalid option.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Error: quantity must be an integer.")
            return
        if self.users:
            info = self.list_manager.get_group_info(self.users)
            print("Available groups: " + ", ".join(info.keys()))
        groups_text = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        drawer = self._ask("Associated lottery person (blank for none): ").strip() or None
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"{index}. {prize.name} | Quantity: {prize.quantity} | Level: {prize.level} "
                f"| Avoid groups: {groups} | Lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask(f"Enter new order as serial numbers (1-{len(prizes)}), e.g. 2 1 3: ")
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid order: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery process -----------------------------------------------

    def _run_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return

        self.lottery = LotteryManager(self.users)
        print("\nLottery starts!")
        print("Commands during drawing: 'pause' | 'continue' | 'terminate' (ends current round).")
        for number, prize in enumerate(prizes, start=1):
            self._run_round(number, prize)
        print("\nAll lottery rounds have been processed.")
        self._show_results()

    def _run_round(self, number: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {number}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {self.lottery.rule_description(prize)}")

        drawn: list[User] = []
        terminated = False
        for order in range(1, prize.quantity + 1):
            if self._checkpoint():
                terminated = True
                break
            print(f"Currently drawing the {_ordinal(order)} winner...", flush=True)
            time.sleep(DRAW_DELAY_SECONDS)
            if self._checkpoint():
                terminated = True
                break
            user = self.lottery.draw_next(prize)
            if user is None:
                print("No eligible participants remain for this prize.")
                break
            drawn.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.lottery.complete_round(prize, drawn)

        if terminated:
            print(f"Round terminated by command. {len(drawn)} of {prize.quantity} winner(s) drawn.")
        elif len(drawn) < prize.quantity:
            print(f"Only {len(drawn)} of {prize.quantity} winner(s) could be drawn.")
        else:
            print("Round complete.")

        if drawn:
            print("Round results (in winning order):")
            for index, user in enumerate(drawn, start=1):
                print(f"  {index}. {user.name} ({user.department})")

    def _checkpoint(self) -> bool:
        """Process pending control commands. Returns True if the round must end."""
        item = self.channel.poll()
        while item is not NO_INPUT:
            if item is END_OF_INPUT:
                raise EOFError
            command = item.strip().lower()
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    reply = self.channel.get()
                    if reply is END_OF_INPUT:
                        raise EOFError
                    reply = reply.strip().lower()
                    if reply == "continue":
                        print("Lottery resumed.")
                        break
                    if reply == "terminate":
                        return True
                    if reply:
                        print("Lottery is paused. Type 'continue' or 'terminate'.")
            elif command == "terminate":
                return True
            elif command == "continue":
                print("Lottery is not paused.")
            elif command:
                print(f"Unknown command '{item}'. Available: pause, continue, terminate.")
            item = self.channel.poll()
        return False

    # ----- results -------------------------------------------------------

    def _show_results(self) -> None:
        if self.lottery is None:
            print("No lottery has been run yet.")
            return
        prizes = self.prize_manager.get_prizes()
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        print("\n=== Winner List ===")
        total = 0
        for prize_name, winners in grouped.items():
            print(f"\n[{prize_name}]")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                total += 1
                print(
                    f"  {winner.winning_order}. {winner.user.name} ({winner.user.department}) "
                    f"- {winner.winning_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        print(f"\nTotal winners: {total}")

    def _export_results(self) -> None:
        if self.lottery is None:
            print("No lottery has been run yet.")
            return
        prizes = self.prize_manager.get_prizes()
        _, message = self.lottery.result_manager.export_to_csv(prizes)
        print(message)


def main() -> None:
    """Entry point for the lottery system."""
    LotteryApp().run()
