"""Command-line interface for the lottery system."""

from __future__ import annotations

import re

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager, infer_level
from lottery_system.services.result_manager import ResultManager, Winner


def ordinal(number: int) -> str:
    """Format an integer as an English ordinal (1st, 2nd, 3rd, 4th, 11th...)."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive console application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.result_manager: ResultManager | None = None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt)

    def _ask_int(self, prompt: str) -> int:
        while True:
            text = self._ask(prompt).strip()
            try:
                value = int(text)
            except ValueError:
                print("Please enter a valid integer.")
                continue
            if value <= 0:
                print("Please enter a positive integer.")
                continue
            return value

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("=" * 60)
        print("   Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._load_default_list()
            elif choice == "2":
                self._load_custom_list()
            elif choice == "3":
                self._show_groups()
            elif choice == "4":
                self._prize_menu()
            elif choice == "5":
                self._start_lottery()
            elif choice == "6":
                self._export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    @staticmethod
    def _print_main_menu() -> None:
        print("\n--- Main Menu ---")
        print("1. Load default team building list")
        print("2. Load custom txt list (Name,Department per line)")
        print("3. View department groups")
        print("4. Prize configuration")
        print("5. Start lottery")
        print("6. Export winner results")
        print("0. Exit")

    # ------------------------------------------------------------ participants
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._verify_and_store(users, errors)

    def _load_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt file: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        self._verify_and_store(users, errors)

    def _verify_and_store(self, users: list[User], errors: list[str]) -> None:
        valid_users, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate Name: {user.name} ({user.department}) - duplicate entry ignored"
            for user in duplicates
        )

        if not problems:
            self.users = valid_users
            print(f"List loaded successfully. Total participants: {len(self.users)}")
            self._show_groups()
            return

        print("Verification found the following issues:")
        for problem in problems:
            print(f"  - {problem}")
        print(f"Valid participants: {len(valid_users)}")

        if not valid_users:
            print("No valid participants remain. Upload terminated; list unchanged.")
            return

        choice = self._ask(
            "Enter 'r' to remove invalid data and continue, 't' to terminate upload: "
        ).strip().lower()
        if choice == "r":
            self.users = valid_users
            print(f"Invalid data removed. Total participants: {len(self.users)}")
            self._show_groups()
        else:
            print("Upload terminated; list unchanged.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nDepartment groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department}: {count} people")
        print(f"Total: {len(self.users)} people in {len(info)} groups")

    # ----------------------------------------------------------------- prizes
    def _prize_menu(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes")
            print("4. Reorder prizes (lottery sequence)")
            print("5. Set avoidance groups for a prize")
            print("6. Remove a prize")
            print("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._edit_avoid_groups()
            elif choice == "6":
                self._remove_prize()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize list (lottery sequence):")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Drawer: {drawer} | Avoid groups: {avoid}"
            )

    def _parse_group_input(self, text: str) -> list[str]:
        """Accept group numbers (from the group list) or group names, comma separated."""
        groups_available = list(self.list_manager.get_group_info(self.users).keys())
        result: list[str] = []
        for token in re.split(r"[,，]", text):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups_available):
                result.append(groups_available[int(token) - 1])
            else:
                result.append(token)
        return result

    def _show_available_groups(self) -> None:
        if not self.users:
            print("(No participant list loaded; group names can still be typed manually.)")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Available groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department} ({count})")

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        quantity = self._ask_int("Prize quantity: ")
        drawer = self._ask("Associated lottery person (leave blank for none): ").strip() or None
        self._show_available_groups()
        groups_text = self._ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        groups = self._parse_group_input(groups_text)
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")

    def _reorder_prizes(self) -> None:
        self._show_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        text = self._ask(
            "Enter the new order as serial numbers separated by spaces or commas "
            "(e.g. 2 1 3): "
        )
        tokens = [token for token in re.split(r"[\s,，]+", text.strip()) if token]
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self._show_prizes()
        else:
            print("Invalid order: every serial number must appear exactly once.")

    def _edit_avoid_groups(self) -> None:
        self._show_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        position = self._ask_int("Prize serial number: ")
        self._show_available_groups()
        groups_text = self._ask("New avoidance groups (blank for none): ")
        groups = self._parse_group_input(groups_text)
        if self.prize_manager.update_avoid_groups(position, groups):
            print("Avoidance groups updated.")
        else:
            print("Invalid prize serial number.")

    def _remove_prize(self) -> None:
        self._show_prizes()
        if not self.prize_manager.get_prizes():
            return
        position = self._ask_int("Prize serial number to remove: ")
        if self.prize_manager.remove_prize(position):
            print("Prize removed.")
        else:
            print("Invalid prize serial number.")

    # --------------------------------------------------------------- lottery
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please configure prizes first.")
            return

        print("\nLottery starts! Controls at each draw: [Enter]=draw, 'pause', 'terminate'.")
        lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()

        for prize in prizes:
            round_winners = self._run_round(lottery, prize, self.result_manager)
            print(f"\n--- Round results: {prize.name} ---")
            if round_winners:
                for winner in round_winners:
                    print(
                        f"  {winner.winning_order}. {winner.user.name} "
                        f"({winner.user.department})"
                    )
            else:
                print("  No winners in this round.")

        self._print_final_summary(prizes)

    def _run_round(self, lottery: LotteryManager, prize: Prize, results: ResultManager) -> list[Winner]:
        print(f"\n===== Round: {prize.name} | Quantity: {prize.quantity} =====")
        print(f"Rules: {lottery.describe_rule(prize)}")

        round_winners: list[Winner] = []
        drawn = 0
        while drawn < prize.quantity:
            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            command = self._ask("> ").strip().lower()

            if command == "pause":
                command = self._wait_while_paused()

            if command == "terminate":
                print("Current round terminated; remaining slots skipped.")
                break
            if command not in ("", "continue"):
                print("Unknown command. Press Enter to draw, 'pause' or 'terminate'.")
                continue

            winner_user = lottery.draw_one(prize)
            if winner_user is None:
                print("No eligible candidates remain for this prize. Round ends.")
                break

            drawn += 1
            winner = results.add_winner(winner_user, prize)
            round_winners.append(winner)
            print(
                f"Congratulations {winner_user.name} ({winner_user.department}) "
                f"for winning {prize.name}!"
            )
        return round_winners

    def _wait_while_paused(self) -> str:
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._ask("[PAUSED] > ").strip().lower()
            if command in ("continue", "terminate"):
                if command == "continue":
                    print("Lottery resumed.")
                return command
            print("Unknown command. Type 'continue' or 'terminate'.")

    def _print_final_summary(self, prizes: list[Prize]) -> None:
        if self.result_manager is None:
            return
        print("\n========== Final Winner List ==========")
        ordered_prizes = [
            prize for _, prize in sorted(
                enumerate(prizes), key=lambda item: (-item[1].level, item[0])
            )
        ]
        grouped = self.result_manager.get_winners_by_prize(ordered_prizes)
        any_winner = False
        for prize in ordered_prizes:
            winners = grouped.get(prize.name, [])
            if not winners:
                continue
            any_winner = True
            print(f"\n[{prize.name}]")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.user.name} "
                    f"({winner.user.department})"
                )
        if not any_winner:
            print("No winners were drawn.")

    # ---------------------------------------------------------------- export
    def _export_results(self) -> None:
        if self.result_manager is None:
            print("No lottery results yet. Please run the lottery first.")
            return
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    """Application entry point."""
    try:
        LotteryCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting lottery system.")
