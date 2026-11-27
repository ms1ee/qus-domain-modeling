"""Command-line interaction for the lottery system."""

import re

from lottery_system.models import CHENG_RU_GROUP, DRAWERS, LI_BIN, MA_JIAQI, User, same_text
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


def _split_tokens(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,]+", text.strip()) if token]


class LotteryCLI:
    """Interactive command-line controller for the whole lottery workflow."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    @staticmethod
    def _title(text: str) -> None:
        print()
        print("=" * 60)
        print(text)
        print("=" * 60)

    def _confirm(self, prompt: str) -> bool:
        return self._ask(prompt).lower() in ("y", "yes")

    @staticmethod
    def _parse_selection(text: str, options: list[str]) -> list[str] | None:
        """Parse comma/space separated option numbers. Returns None if invalid."""
        tokens = _split_tokens(text)
        chosen: list[str] = []
        for token in tokens:
            if not token.isdigit():
                return None
            index = int(token)
            if not 1 <= index <= len(options):
                return None
            if options[index - 1] not in chosen:
                chosen.append(options[index - 1])
        return chosen

    # ------------------------------------------------------------------ #
    # Entry
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        try:
            return self._run_flow()
        except (EOFError, KeyboardInterrupt):
            print("\nLottery session ended.")
            return 1

    def _run_flow(self) -> int:
        self._title("Company Team Building Smart Lottery System")

        if not self._setup_user_list():
            print("No participant list loaded. Exiting.")
            return 0

        self._show_group_info()
        self._setup_prizes()

        if not self.prize_manager.get_prizes():
            print("No prizes configured. Exiting.")
            return 0

        if not self._confirm("\nStart the lottery now? (y/n): "):
            print("Lottery cancelled.")
            return 0

        self._run_lottery()
        self._show_summary()
        self._export_results()
        print("\nThank you for using the lottery system.")
        return 0

    # ------------------------------------------------------------------ #
    # List management
    # ------------------------------------------------------------------ #
    def _setup_user_list(self) -> bool:
        while True:
            self._title("List Loading")
            print("1. Load built-in default team building list")
            print("2. Upload custom txt list (format: Name,Department Group per line)")
            print("0. Exit")
            choice = self._ask("Select an option: ")

            if choice == "0":
                return False
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
            elif choice == "2":
                path = self._ask("Enter the txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
            else:
                print("Invalid option.")
                continue

            valid_users = self._verify_list(users, errors)
            if valid_users is None:
                continue

            self.users = valid_users
            print(f"Loaded {len(valid_users)} valid participants.")
            return True

    def _verify_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        valid_users, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            return valid_users

        print("\nList verification found problems:")
        for error in errors:
            print(f"  - {error}")
        for duplicate in duplicates:
            print(
                f"  - Duplicate Name: '{duplicate.name}' ({duplicate.department}) "
                "appears more than once; only the first occurrence is kept"
            )
        print(f"Valid participants available: {len(valid_users)}")
        print("1. Remove invalid data and continue with valid participants")
        print("2. Terminate upload")
        choice = self._ask("Select an option: ")

        if choice == "1":
            if not valid_users:
                print("No valid participants remain.")
                return None
            return valid_users

        print("Upload terminated.")
        return None

    def _show_group_info(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        self._title("Department Groups")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self.users)} people in {len(info)} groups")

    # ------------------------------------------------------------------ #
    # Prize configuration
    # ------------------------------------------------------------------ #
    def _setup_prizes(self) -> None:
        while True:
            self._title("Prize Configuration")
            print("1. Load preset prizes")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Reorder lottery rounds")
            print("5. View prize list")
            print("0. Finish configuration")
            choice = self._ask("Select an option: ")

            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_prize_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._show_prizes()
            elif choice == "0":
                if self.prize_manager.get_prizes():
                    return
                print("Please add at least one prize before starting.")
            else:
                print("Invalid option.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Lottery rounds (in order):")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "None"
            groups = ", ".join(prize.avoid_groups) or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {groups}"
            )

    def _choose_drawer(self) -> str | None:
        print("Associated lottery person:")
        for index, drawer in enumerate(DRAWERS, start=1):
            print(f"  {index}. {drawer}")
        print("  0. None")
        while True:
            choice = self._ask("Select lottery person: ")
            if choice in ("", "0"):
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(DRAWERS):
                return DRAWERS[int(choice) - 1]
            print("Invalid selection.")

    def _choose_groups(self) -> list[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if not groups:
            return []
        print("Avoidance groups (enter numbers separated by commas; empty for none):")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        while True:
            selection = self._parse_selection(self._ask("Select groups: "), groups)
            if selection is not None:
                return selection
            print("Invalid selection, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Prize quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            print("Error: quantity must be a positive integer.")
            return
        drawer = self._choose_drawer()
        groups = self._choose_groups()
        try:
            prize = self.prize_manager.add_prize(name, int(quantity_text), groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {prize.name} (x{prize.quantity})")

    def _set_prize_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name}")
        choice = self._ask("Select prize number: ")
        if not choice.isdigit() or not 1 <= int(choice) <= len(prizes):
            print("Invalid prize number.")
            return
        prize = prizes[int(choice) - 1]
        groups = self._choose_groups()
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoidance groups updated for {prize.name}.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are required to reorder.")
            return
        print("Current order:")
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name}")
        tokens = _split_tokens(self._ask("Enter new order as serial numbers (e.g. 2 1 3): "))
        if not tokens or not all(token.isdigit() for token in tokens):
            print("Invalid input: please enter serial numbers only.")
            return
        order = [int(token) for token in tokens]
        if self.prize_manager.reorder_prizes(order):
            print("Lottery round order updated.")
        else:
            print("Invalid order: each serial number must be used exactly once.")

    # ------------------------------------------------------------------ #
    # Lottery process
    # ------------------------------------------------------------------ #
    def _run_lottery(self) -> None:
        prizes = self.prize_manager.get_prizes()
        self.lottery = LotteryManager(self.users)
        self._title("Lottery Started")
        total = len(prizes)
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
        print("\nAll lottery rounds completed.")

    def _describe_rules(self, prize) -> str:
        assert self.lottery is not None
        drawer = prize.associated_drawer
        rules = [f"Lottery person: {drawer or 'None'}"]
        if drawer and same_text(drawer, LI_BIN):
            rules.append("Only previous winners are excluded (avoidance groups not applied)")
        elif (
            drawer
            and same_text(drawer, MA_JIAQI)
            and self.lottery.is_cheng_ru_fallback_active()
        ):
            rules.append(
                f"Cheng Ru Group protection active: only {CHENG_RU_GROUP} members are eligible"
            )
        else:
            rules.append("Previous winners are excluded")
            if prize.avoid_groups:
                rules.append("Avoided groups: " + ", ".join(prize.avoid_groups))
        return "; ".join(rules)

    def _await_command(self) -> str:
        """Wait for user input before each draw. Returns 'draw' or 'terminate'."""
        while True:
            command = self._ask("Press Enter to draw, or type 'pause' / 'terminate': ").lower()
            if command == "":
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused.")
                while True:
                    resume = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if resume == "terminate":
                        return "terminate"
                    print("Unknown command.")
            print("Unknown command.")

    def _run_round(self, index: int, total: int, prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {index}/{total}: {prize.name} ===")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {self._describe_rules(prize)}")

        round_winners: list[User] = []
        terminated = False

        for position in range(1, prize.quantity + 1):
            print(f"Currently drawing the {_ordinal(position)} winner...")
            command = self._await_command()
            if command == "terminate":
                terminated = True
                break

            winner = self.lottery.draw_one(prize)
            if winner is None:
                print("No eligible candidates remain for this prize; the round ends early.")
                break

            self.result_manager.add_winner(winner, prize)
            round_winners.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}!")

        self.lottery.record_round_result(prize, round_winners)

        print(f"\nRound results for {prize.name}:")
        if round_winners:
            for order, winner in enumerate(round_winners, start=1):
                print(f"  {order}. {winner.name} ({winner.department})")
        else:
            print("  (no winners)")

        if terminated:
            print(f"Round terminated early: {len(round_winners)}/{prize.quantity} winners drawn.")
        elif len(round_winners) < prize.quantity:
            print(f"Round ended with {len(round_winners)}/{prize.quantity} winners.")

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #
    def _show_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._title("Final Winner List")
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
                continue
            for winner in winners:
                print(
                    f"  {winner.win_order}. {winner.user.name} "
                    f"({winner.user.department})"
                )

    def _export_results(self) -> None:
        if not self._confirm("\nExport the winner list to file? (y/n): "):
            return
        _, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> int:
    """Start the interactive lottery system."""
    return LotteryCLI().run()
