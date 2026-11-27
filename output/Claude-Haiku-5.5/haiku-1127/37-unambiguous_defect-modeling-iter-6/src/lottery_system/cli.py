"""Command-line interaction for the lottery process, prizes, lists and results."""
from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import Winner, sort_prizes_by_level

LOTTERY_PERSONS: list[str] = ["Li Bin", "Chen Qixian", "Jin Duo", "Ma Jiaqi"]


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ----- input helpers ------------------------------------------------------
    @staticmethod
    def _ask(prompt: str = "") -> str:
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(0)

    def _ask_int(self, prompt: str, minimum: int = 1) -> int:
        while True:
            raw = self._ask(prompt)
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a valid integer.")
                continue
            if value < minimum:
                print(f"Please enter a number >= {minimum}.")
                continue
            return value

    def _ask_groups(self, prompt: str) -> list[str]:
        raw = self._ask(prompt)
        groups = [item.strip() for item in raw.split(",") if item.strip()]
        known = {user.department.casefold() for user in self.users}
        if self.users:
            for group in groups:
                if group.casefold() not in known:
                    print(f"Warning: group '{group}' does not exist in the current list.")
        return groups

    # ----- main loop ----------------------------------------------------------
    def run(self) -> None:
        print("=" * 60)
        print("Company Team Building - Smart Lottery System")
        print("=" * 60)
        if self._ask("Load the preset prize library now? [Y/n]: ").casefold() in ("", "y", "yes"):
            for error in self.prize_manager.load_default_prizes():
                print(error)
            print("Preset prizes loaded.")

        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ")
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.manage_prizes()
            elif choice == "4":
                self.adjust_sequence()
            elif choice == "5":
                self.start_lottery()
            elif choice == "6":
                self.show_results()
            elif choice == "7":
                self.export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    @staticmethod
    def _print_main_menu() -> None:
        print()
        print("---------------- Main Menu ----------------")
        print("  1. Load participant list")
        print("  2. View department groups")
        print("  3. Configure prizes")
        print("  4. Adjust prize sequence")
        print("  5. Start lottery")
        print("  6. View winner results")
        print("  7. Export results to txt")
        print("  0. Exit")
        print("-------------------------------------------")

    def _print_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        print()
        if not prizes:
            print("No prizes configured.")
            return
        print("Current prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} "
                f"| lottery person: {drawer} | avoid groups: {avoid}"
            )

    # ----- participant list ---------------------------------------------------
    def load_participants(self) -> None:
        print("1. Built-in default team building list")
        print("2. Custom txt list (format per line: Name,Department)")
        choice = self._ask("Select list source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid option.")
            return

        valid_users, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self._commit_list(valid_users)
            return

        print()
        print("List verification found problems:")
        for error in errors:
            print(f"  {error}")
        for user in duplicates:
            print(f"  Duplicate Name: '{user.name}' ({user.department}) ignored")
        print()
        print("  1. Remove invalid data and keep valid entries")
        print("  2. Manually remove specific names, then keep the rest")
        print("  3. Terminate upload")
        action = self._ask("Select action: ")

        if action == "1":
            self._commit_list(valid_users)
        elif action == "2":
            raw = self._ask("Enter names to remove (comma separated): ")
            to_remove = {item.strip().casefold() for item in raw.split(",") if item.strip()}
            kept = [user for user in valid_users if user.name.casefold() not in to_remove]
            self._commit_list(kept)
        else:
            print("Upload terminated. Participant list unchanged.")

    def _commit_list(self, users: list[User]) -> None:
        if not users:
            print("No valid participants; the list was not loaded.")
            return
        self.users = list(users)
        print(f"Participant list loaded: {len(self.users)} valid participant(s).")

    def show_groups(self) -> None:
        if not self.users:
            print("Please load the participant list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} member(s)")
        print(f"Total groups: {len(info)}, total participants: {len(self.users)}")

    # ----- prizes -------------------------------------------------------------
    def manage_prizes(self) -> None:
        while True:
            self._print_prizes()
            print()
            print("  1. Load preset prize library")
            print("  2. Add custom prize")
            print("  3. Set avoidance groups for a prize")
            print("  0. Back")
            choice = self._ask("Select option: ")
            if choice == "1":
                for error in self.prize_manager.load_default_prizes():
                    print(error)
                print("Preset prizes processed.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_int("Quantity: ", 1)
        print("Available lottery persons: " + ", ".join(LOTTERY_PERSONS))
        drawer = self._ask("Associated lottery person (blank for none): ") or None
        groups = self._ask_groups("Avoidance groups (comma separated, blank for none): ")
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print(f"Prize added: {prize.name}")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._print_prizes()
        index = self._ask_int("Prize number: ", 1)
        if index > len(prizes):
            print("Prize number out of range.")
            return
        groups = self._ask_groups("Avoidance groups (comma separated, blank for none): ")
        prize = prizes[index - 1]
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoidance groups updated for '{prize.name}': {', '.join(groups) or 'None'}")

    def adjust_sequence(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to adjust the sequence.")
            return
        self._print_prizes()
        raw = self._ask("Enter new order as serial numbers, e.g. '2 1 3' (blank to cancel): ")
        if not raw:
            return
        try:
            order = [int(item) for item in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
            self._print_prizes()
        else:
            print(f"Invalid order: must contain each number 1-{len(prizes)} exactly once.")

    # ----- lottery process ----------------------------------------------------
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is not None:
            print("A lottery has already been run in this session. Showing results instead.")
            self.show_results()
            return

        self.lottery = LotteryManager(self.users)
        print()
        print("Lottery started. Commands: Enter = draw next, 'pause', 'terminate' (end round).")
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
        print()
        print("All lottery rounds completed!")
        self.show_results()

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print()
        print(f"=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Lottery person: {prize.associated_drawer or 'Not specified'}")
        print(f"Rule: {self.lottery.describe_rules(prize)}")

        round_winners: list[Winner] = []
        drawn = 0
        while drawn < prize.quantity:
            command = self._ask("Press Enter to draw next winner (pause / terminate): ").casefold()
            if command == "pause":
                if not self._wait_for_resume():
                    print("Round terminated, skipping to the next round.")
                    break
            elif command == "terminate":
                print("Round terminated, skipping to the next round.")
                break
            elif command not in ("", "continue"):
                print("Unknown command. Use Enter, 'pause' or 'terminate'.")
                continue

            print(f"Currently drawing the {_ordinal(drawn + 1)} winner...")
            winner = self.lottery.draw_next(prize)
            if winner is None:
                print("No eligible participants remain for this prize; round ends.")
                break
            round_winners.append(winner)
            drawn += 1
            user = winner.user
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self.lottery.record_round_result(prize, round_winners)
        print(f"Round {index} finished: {len(round_winners)} of {prize.quantity} winner(s) drawn.")

    @staticmethod
    def _wait_for_resume() -> bool:
        """Block while paused. Returns True to resume, False to terminate the round."""
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = LotteryCLI._ask("> ").casefold()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Lottery is paused. Type 'continue' or 'terminate'.")

    # ----- results ------------------------------------------------------------
    def show_results(self) -> None:
        if self.lottery is None:
            print("No lottery results yet.")
            return
        prizes = sort_prizes_by_level(self.prize_manager.get_prizes())
        grouped = self.lottery.result_manager.get_winners_by_prize(prizes)
        print()
        print("==================== Winner List ====================")
        for prize_name, winners in grouped.items():
            print(f"[{prize_name}]")
            if not winners:
                print("  (no winners)")
                continue
            for position, winner in enumerate(winners, start=1):
                user = winner.user
                print(f"  {position}. {user.name} ({user.department})")
        print("=====================================================")

    def export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export.")
            return
        _, message = self.lottery.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    """Application entry point."""
    LotteryCLI().run()
