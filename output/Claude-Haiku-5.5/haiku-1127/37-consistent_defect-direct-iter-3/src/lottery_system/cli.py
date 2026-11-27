"""Command-line interface for the team building smart lottery system."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAWER_CHOICES = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

MAIN_MENU = """
==================== Main Menu ====================
1. Load participant list
2. View department groups
3. Prize configuration
4. Start lottery
5. Show results
6. Export results
0. Exit
===================================================="""


def ordinal(number: int) -> str:
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
        self.lottery_manager: LotteryManager | None = None
        self.completed_prizes: set[str] = set()
        self._handlers = {
            "1": self.load_list_menu,
            "2": self.show_groups,
            "3": self.prize_menu,
            "4": self.start_lottery,
            "5": self.show_results,
            "6": self.export_results,
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _available_groups(self) -> list[str]:
        if not self.users:
            return []
        return list(self.list_manager.get_group_info(self.users).keys())

    # ---------------------------------------------------------------- main loop
    def run(self) -> None:
        print("Company Team Building - Smart Lottery System")
        try:
            while True:
                print(MAIN_MENU)
                choice = self._ask("Select an option: ")
                if choice == "0":
                    print("Goodbye!")
                    return
                handler = self._handlers.get(choice)
                if handler is None:
                    print("Invalid option, please try again.")
                else:
                    handler()
        except (EOFError, KeyboardInterrupt):
            print("\nLottery system closed.")

    # ------------------------------------------------------------ list module
    def load_list_menu(self) -> None:
        if self.result_manager.has_winners():
            print("The lottery already has results; the participant list can no longer be changed.")
            return
        print("1. Built-in default team building list")
        print("2. Upload custom txt list (each line: Name,Department Group)")
        choice = self._ask("Select list source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter the txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid option.")
            return

        final_users = self._verify_users(users, errors)
        if final_users is None:
            print("List upload terminated. Current list is unchanged.")
            return
        if not final_users:
            print("No valid participants found. Current list is unchanged.")
            return

        self.users = final_users
        self.lottery_manager = LotteryManager(self.users)
        self.completed_prizes.clear()
        print(f"Loaded {len(final_users)} participant(s).")
        self.show_groups()

    def _verify_users(self, users: list[User], errors: list[str]) -> list[User] | None:
        """Report errors/duplicates. Returns the valid users, or None if terminated."""
        if errors:
            print(f"Found {len(errors)} format error(s):")
            for error in errors:
                print(f"  {error}")
        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  Duplicate: {user.name} ({user.department})")
        if not errors and not duplicates:
            return valid

        print("Options: 'r' = remove invalid data and continue, 't' = terminate upload")
        while True:
            choice = self._ask("Your choice (r/t): ").lower()
            if choice == "r":
                return valid
            if choice == "t":
                return None
            print("Please enter 'r' or 't'.")

    def show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Valid department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department}: {count} people")

    # ---------------------------------------------------------- prize module
    def prize_menu(self) -> None:
        while True:
            print("\n---------------- Prize Configuration ----------------")
            print("1. Show prizes")
            print("2. Load preset prize library")
            print("3. Add custom prize")
            print("4. Configure avoidance groups / lottery person of a prize")
            print("5. Reorder lottery sequence")
            print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "0":
                return
            if choice == "1":
                self.show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  {error}")
                else:
                    print("Preset prize library loaded.")
            elif choice == "3":
                self.add_custom_prize()
            elif choice == "4":
                self.configure_prize()
            elif choice == "5":
                self.reorder_prizes_menu()
            else:
                print("Invalid option.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoidance groups: {groups}"
            )

    def _ask_groups(self) -> list[str]:
        groups = self._available_groups()
        if groups:
            print("Available department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        text = self._ask("Avoidance groups (numbers or names, comma-separated; blank for none): ")
        result: list[str] = []
        for token in (part.strip() for part in text.split(",")):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
            else:
                name = token
            if name not in result:
                result.append(name)
        return result

    def _ask_drawer(self) -> str | None:
        print("Associated lottery person: 0. None | 1. Chen Qixian | 2. Jin Duo | "
              "3. Ma Jiaqi | 4. Li Bin (or type a name)")
        text = self._ask("Choice (blank for none): ")
        if not text:
            return None
        if text.isdigit():
            number = int(text)
            if number == 0:
                return None
            if 1 <= number <= len(DRAWER_CHOICES):
                return DRAWER_CHOICES[number - 1]
            print("Invalid choice; no lottery person set.")
            return None
        return text

    def add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be an integer.")
            return
        groups = self._ask_groups()
        drawer = self._ask_drawer()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_prize(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.show_prizes()
        text = self._ask("Select prize number to configure: ")
        if not text.isdigit() or not 1 <= int(text) <= len(prizes):
            print("Invalid prize number.")
            return
        prize = prizes[int(text) - 1]
        groups = self._ask_groups()
        drawer = self._ask_drawer()
        if self.prize_manager.configure_prize(prize.name, groups, drawer):
            print("Prize configuration updated.")
        else:
            print("Prize not found.")

    def reorder_prizes_menu(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.show_prizes()
        text = self._ask("Enter new order as serial numbers separated by spaces (e.g. 3 1 2): ")
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            print("Order must contain only serial numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self.show_prizes()
        else:
            print("Invalid order: each prize number must appear exactly once.")

    # ------------------------------------------------------ lottery control
    def start_lottery(self) -> None:
        if not self.users or self.lottery_manager is None:
            print("Load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Configure at least one prize first.")
            return

        print("\nLottery sequence:")
        self.show_prizes()
        for round_no, prize in enumerate(prizes, start=1):
            if prize.name in self.completed_prizes:
                print(f"Round {round_no} ({prize.name}) already completed; skipping.")
                continue
            self._run_round(round_no, prize)

        print("\nAll rounds finished.")
        self.show_results()

    def _run_round(self, round_no: int, prize) -> None:
        print("\n" + "=" * 64)
        print(f"Round {round_no}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {LotteryManager.describe_rule(prize)}")
        print("=" * 64)
        print("Commands: Enter = draw next winner | pause | continue | terminate (skip round)")

        drawn: list = []
        paused = False
        while len(drawn) < prize.quantity:
            position = len(drawn) + 1
            status = " [PAUSED]" if paused else ""
            command = self._ask(
                f"Currently drawing the {ordinal(position)} winner{status} > "
            ).lower()

            if command == "pause":
                if paused:
                    print("Lottery is already paused.")
                else:
                    paused = True
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip the round.")
                continue
            if command == "continue":
                if paused:
                    paused = False
                    print("Lottery resumed.")
                else:
                    print("Lottery is not paused.")
                continue
            if command == "terminate":
                print(f"Round terminated. {len(drawn)} of {prize.quantity} winner(s) drawn.")
                break
            if command != "":
                print("Unknown command. Use Enter, pause, continue or terminate.")
                continue
            if paused:
                print("Lottery is paused. Type 'continue' to resume.")
                continue

            user = self.lottery_manager.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            drawn.append(winner)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"\nRound {round_no} results ({prize.name}):")
        if not drawn:
            print("  (no winners in this round)")
        for index, winner in enumerate(drawn, start=1):
            print(f"  {index}. {winner.user.name} ({winner.user.department})")
        self.completed_prizes.add(prize.name)

    # -------------------------------------------------------- results module
    def show_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.result_manager.has_winners():
            print("No winners yet.")
            return
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n==================== Winner List ====================")
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}")
            if not winners:
                print("  (no winners)")
            for index, winner in enumerate(winners, start=1):
                print(
                    f"  {index}. {winner.user.name} ({winner.user.department})"
                    f"  [{winner.won_at:%H:%M:%S}]"
                )

    def export_results(self) -> None:
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    LotterySystemCLI().run()
