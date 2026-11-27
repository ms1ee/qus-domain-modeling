"""Command-line interface for the team building lottery system."""

from __future__ import annotations

from lottery_system.models import CHENG_RU_GROUP, LI_BIN, LOTTERY_PERSONS, MA_JIAQI, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str) -> str:
        return input(prompt).strip()

    def _choose_option(self, options: list[str]) -> int:
        """Show numbered options and return the chosen 1-based index."""
        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")
        while True:
            choice = self._ask("Select: ")
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return int(choice)
            print("Invalid option, please try again.")

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            print("\n=== Main Menu ===")
            print("1. Load participant list")
            print(f"   (currently loaded: {len(self.users)} participants)")
            print("2. View department groups")
            print("3. Prize configuration")
            print("4. Start lottery")
            print("0. Exit")
            choice = self._ask("Select: ")
            if choice == "1":
                self._load_list_menu()
            elif choice == "2":
                self._view_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------------ list module
    def _load_list_menu(self) -> None:
        print("\n=== Load Participant List ===")
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (format: Name,Department Group)")
        print("0. Back")
        choice = self._ask("Select: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            for error in errors:
                print(error)
            self.users = users
            print(f"Default list loaded: {len(users)} participants.")
        elif choice == "2":
            self._load_custom_list()

    def _load_custom_list(self) -> None:
        path = self._ask("Enter txt file path (blank to cancel): ")
        if not path:
            return
        users, errors = self.list_manager.load_custom_list(path)
        if errors:
            print("Problems found in the file:")
            for error in errors:
                print(f"  {error}")
            if not users:
                print("No valid data found. Upload aborted.")
                return
            print("Choose how to proceed:")
            if self._choose_option(["Remove invalid entries and continue",
                                    "Terminate upload"]) == 2:
                print("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print("Duplicate names found (later occurrences):")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            print("Choose how to proceed:")
            if self._choose_option(["Remove duplicates (keep first occurrence) and continue",
                                    "Terminate upload"]) == 2:
                print("Upload terminated.")
                return

        if not valid:
            print("No valid participants. Upload aborted.")
            return
        self.users = valid
        print(f"Custom list loaded: {len(valid)} participants.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\n=== Department Groups ===")
        for group, count in info.items():
            print(f"  {group}: {count} people")
        print(f"  Total groups: {len(info)}, total people: {len(self.users)}")

    # ----------------------------------------------------------- prize module
    def _prize_menu(self) -> None:
        while True:
            print("\n=== Prize Configuration ===")
            print("1. Add custom prize")
            print("2. Load preset prize library")
            print("3. View prize list")
            print("4. Adjust lottery order")
            print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                self._add_prize()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(f"Error: {error}")
                print("Preset prizes loaded.")
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_raw = self._ask("Quantity: ")
        if not quantity_raw.lstrip("-").isdigit():
            print("Error: quantity must be a positive integer.")
            return
        quantity = int(quantity_raw)

        print("Associated lottery person:")
        drawer_options = ["None"] + list(LOTTERY_PERSONS)
        drawer_index = self._choose_option(drawer_options)
        drawer = None if drawer_index == 1 else drawer_options[drawer_index - 1]

        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid_groups: list[str] = []
        if groups:
            print("Department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        raw = self._ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        for token in [t.strip() for t in raw.split(",") if t.strip()]:
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                avoid_groups.append(groups[int(token) - 1])
            else:
                avoid_groups.append(token)

        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
            print(f"Prize '{name.strip()}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\n=== Prize List (lottery order) ===")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                  f"avoid groups: {avoid} | lottery person: {drawer}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        raw = self._ask("Enter new order as serial numbers (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Error: please enter numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery order updated.")
        else:
            print("Error: order must contain each serial number exactly once.")

    # --------------------------------------------------------- lottery module
    @staticmethod
    def _describe_rules(prize: Prize, lottery: LotteryManager) -> list[str]:
        rules = ["Previous winners are excluded."]
        if prize.associated_drawer == LI_BIN:
            rules.append("Special rule (Li Bin): avoidance groups are NOT applied.")
        elif prize.avoid_groups:
            rules.append("Avoidance groups (" + ", ".join(prize.avoid_groups) + ") are drawn "
                         "only after all other eligible members.")
        if prize.associated_drawer == MA_JIAQI:
            status = " [ACTIVE this round]" if lottery.is_cheng_ru_protection_active(prize) else ""
            rules.append(f"{CHENG_RU_GROUP} protection: if the last two draws by Chen Qixian and "
                         f"Jin Duo had no {CHENG_RU_GROUP} winners, only its members are "
                         f"eligible{status}.")
        if prize.associated_drawer:
            rules.append(f"Lottery person: {prize.associated_drawer}")
        return rules

    def _wait_for_command(self, prompt: str) -> str:
        """Handle pause / continue / terminate. Returns 'continue' or 'terminate'."""
        while True:
            command = self._ask(prompt).lower()
            if command in ("", "continue"):
                return "continue"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("[paused] > ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return "continue"
                    if resume == "terminate":
                        return "terminate"
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        total_rounds = len(prizes)

        for round_no, prize in enumerate(prizes, start=1):
            print("\n" + "=" * 60)
            print(f"Round {round_no}/{total_rounds}: {prize.name}")
            print(f"Quantity: {prize.quantity}")
            print("Rules:")
            for rule in self._describe_rules(prize, lottery):
                print(f"  - {rule}")
            self._run_round(lottery, prize)

        print("\n" + "=" * 60)
        self._show_final_summary(prizes)
        if self._ask("Export results to txt file? (y/n): ").lower() == "y":
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)

    def _run_round(self, lottery: LotteryManager, prize: Prize) -> None:
        lottery.start_round(prize)
        round_winners: list[tuple[User, int]] = []

        if self._wait_for_command("Press Enter to start this round, 'terminate' to skip: ") == "terminate":
            print("Round skipped.")
            lottery.end_round(prize)
            return

        for position in range(1, prize.quantity + 1):
            print(f"Currently drawing the {_ordinal(position)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append((user, winner.sequence))
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

            if position == prize.quantity:
                break
            if self._wait_for_command(
                "Press Enter to draw next, 'pause' to pause, 'terminate' to end round: "
            ) == "terminate":
                print("Round terminated early.")
                break

        lottery.end_round(prize)
        print(f"\nRound results for {prize.name}:")
        if not round_winners:
            print("  (no winners)")
        for index, (user, sequence) in enumerate(round_winners, start=1):
            print(f"  {index}. {user.name} ({user.department}) [win #{sequence}]")

    def _show_final_summary(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("=== Final Winner List (by prize level, then winning order) ===")
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.sequence}. {winner.user.name} ({winner.user.department})")


def main() -> None:
    """Application entry point."""
    try:
        LotterySystemCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting lottery system.")
