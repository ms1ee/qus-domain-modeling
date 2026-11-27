"""Command-line interface for the team building lottery system."""

from __future__ import annotations

from lottery_system.models import LI_BIN, MA_JIAQI, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MAIN_MENU = """
========== Team Building Lottery System ==========
1. Load participant list
2. View department group information
3. Prize configuration
4. Start lottery
5. View / export results
0. Exit
"""

PRIZE_MENU = """
--- Prize Configuration ---
1. Load preset prizes
2. Add custom prize
3. Set avoidance groups for a prize
4. View prize list (lottery sequence)
5. Reorder lottery sequence
0. Back
"""

RESULT_MENU = """
--- Results ---
1. View results summary
2. Export results to txt (CSV format)
0. Back
"""


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 2nd, 11th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------
    # Input helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _ask_int(self, prompt: str, minimum: int = 1) -> int:
        while True:
            text = self._ask(prompt)
            try:
                value = int(text)
            except ValueError:
                print("Please enter a valid integer.")
                continue
            if value < minimum:
                print(f"Please enter a number >= {minimum}.")
                continue
            return value

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System.")
        while True:
            print(MAIN_MENU)
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
                self.results_menu()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------
    def load_participants(self) -> None:
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (one 'Name,Department' per line)")
        choice = self._ask("Select a loading mode: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter the txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid choice.")
            return

        valid = self._verify_list(users, errors)
        if valid is None:
            print("Upload terminated. The current list is unchanged.")
            return
        self._set_users(valid)
        print(f"Loaded {len(valid)} valid participants.")

    def _verify_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            return valid

        print("\nData verification found problems:")
        for error in errors:
            print(f"  - {error}")
        for duplicate in duplicates:
            print(f"  - Duplicate name: {duplicate.name} ({duplicate.department})")

        if not valid:
            print("No valid participants remain.")
            return None

        while True:
            choice = self._ask(
                "Type 'r' to remove invalid/duplicate data and continue, "
                "or 't' to terminate the upload: "
            ).lower()
            if choice == "r":
                return valid
            if choice == "t":
                return None
            print("Please enter 'r' or 't'.")

    def _set_users(self, users: list[User]) -> None:
        self.users = list(users)
        self.lottery = LotteryManager(self.users, self.result_manager)

    def show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid department groups:")
        for number, (department, count) in enumerate(info.items(), start=1):
            print(f"  {number}. {department}: {count} people")

    # ------------------------------------------------------------------
    # Prize configuration
    # ------------------------------------------------------------------
    def prize_menu(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._load_preset_prizes()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._view_prizes()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(f"  - {error}")
        else:
            print("Preset prizes loaded.")

    def _group_names(self) -> list[str]:
        if not self.users:
            return []
        return list(self.list_manager.get_group_info(self.users).keys())

    def _show_groups_numbered(self, groups: list[str]) -> None:
        if not groups:
            print("(No department groups available; load a participant list first.)")
            return
        print("Available department groups:")
        for number, group in enumerate(groups, start=1):
            print(f"  {number}. {group}")

    def _parse_groups(self, text: str, groups: list[str]) -> list[str]:
        """Parse comma-separated group numbers or names into a list of group names."""
        result: list[str] = []
        normalized = text.replace("\uff0c", ",")
        for token in (part.strip() for part in normalized.split(",")):
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
            else:
                name = next((g for g in groups if g.lower() == token.lower()), token)
            if name not in result:
                result.append(name)
        return result

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity = self._ask_int("Prize quantity: ", 1)
        drawer = self._ask("Associated lottery person (blank for none): ") or None
        groups = self._group_names()
        self._show_groups_numbered(groups)
        avoid_text = self._ask("Avoidance groups (numbers or names, comma separated; blank for none): ")
        avoid_groups = self._parse_groups(avoid_text, groups)
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {self._format_prize(prize)}")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        number = self._ask_int("Select prize number: ", 1)
        if number > len(prizes):
            print("Invalid prize number.")
            return
        prize = prizes[number - 1]
        groups = self._group_names()
        self._show_groups_numbered(groups)
        print(f"Current avoidance groups: {', '.join(prize.avoid_groups) or 'None'}")
        text = self._ask("New avoidance groups (numbers or names, blank to clear): ")
        prize.avoid_groups = self._parse_groups(text, groups)
        print(f"Updated avoidance groups: {', '.join(prize.avoid_groups) or 'None'}")

    @staticmethod
    def _format_prize(prize: Prize) -> str:
        parts = [f"{prize.name} x{prize.quantity}"]
        if prize.associated_drawer:
            parts.append(f"drawer: {prize.associated_drawer}")
        if prize.avoid_groups:
            parts.append(f"avoid: {', '.join(prize.avoid_groups)}")
        return " | ".join(parts)

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nLottery sequence:")
        for number, prize in enumerate(prizes, start=1):
            print(f"  {number}. {self._format_prize(prize)}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        text = self._ask("Enter the new order as serial numbers (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._view_prizes()
        else:
            print("Invalid order: each serial number from 1 to "
                  f"{len(prizes)} must appear exactly once.")

    # ------------------------------------------------------------------
    # Lottery process
    # ------------------------------------------------------------------
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)

        print("\nLottery starts! Rounds in order:")
        for number, prize in enumerate(prizes, start=1):
            print(f"  {number}. {self._format_prize(prize)}")

        for round_no, prize in enumerate(prizes, start=1):
            print(f"\n===== Round {round_no}/{len(prizes)}: {prize.name} =====")
            print(f"Quantity: {prize.quantity}")
            print(f"Rules: {self._describe_rules(prize)}")

            def announce(index: int, total: int, user: User, current: Prize = prize) -> None:
                print(f"Congratulations {user.name} ({user.department}) "
                      f"for winning {current.name}!")

            winners = self.lottery.run_round(
                prize,
                on_winner=announce,
                before_draw=self._before_draw,
            )
            self._print_round_results(prize, winners)

        print("\n========== Final Winner List ==========")
        self._print_summary()

    def _before_draw(self, index: int, total: int) -> bool:
        """Prompt before each draw. Returns False if the round should be terminated."""
        print(f"\nCurrently drawing the {ordinal(index)} winner ({index}/{total})")
        while True:
            command = self._ask("Press Enter to draw, or type 'pause' / 'terminate': ").lower()
            if command == "":
                return True
            if command == "terminate":
                print("Current round terminated and skipped.")
                return False
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("(paused) > ").lower()
                    if resume == "continue":
                        print("Lottery resumed.")
                        return True
                    if resume == "terminate":
                        print("Current round terminated and skipped.")
                        return False
                    print("Please type 'continue' or 'terminate'.")
            print("Unknown command.")

    def _describe_rules(self, prize: Prize) -> str:
        rules = ["previous winners are excluded"]
        drawer = (prize.associated_drawer or "").strip()
        if drawer.lower() == LI_BIN.lower():
            rules.append("relaxed rules for Li Bin (avoidance groups ignored)")
        elif prize.avoid_groups:
            rules.append(f"avoid groups: {', '.join(prize.avoid_groups)}")
        if drawer.lower() == MA_JIAQI.lower():
            rules.append(
                "Cheng Ru Group protection: if the last two Chen Qixian/Jin Duo rounds "
                "had no Cheng Ru Group winners, only Cheng Ru Group members are eligible"
            )
        if drawer:
            rules.insert(0, f"lottery person: {drawer}")
        return "; ".join(rules)

    def _print_round_results(self, prize: Prize, winners: list[User]) -> None:
        if not winners:
            print(f"No winners drawn for {prize.name} (no eligible candidates or round terminated).")
            return
        print(f"\nRound results for {prize.name} (in winning order):")
        for number, user in enumerate(winners, start=1):
            print(f"  {number}. {user.name} ({user.department})")
        if len(winners) < prize.quantity:
            print(f"Note: {len(winners)} of {prize.quantity} winners drawn "
                  f"(round terminated or not enough eligible candidates).")

    def _print_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        has_winners = False
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            has_winners = True
            print(f"\n[{prize_name}]")
            for winner in winners:
                print(f"  #{winner.order:<3} {winner.user.name} ({winner.user.department}) "
                      f"- {prize_name}")
        if not has_winners:
            print("No winners yet.")

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def results_menu(self) -> None:
        while True:
            print(RESULT_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._print_summary()
            elif choice == "2":
                ok, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
                print(message)
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")


def main() -> None:
    try:
        LotterySystemCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting the lottery system.")
