"""Command-line interface for the lottery system."""

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LI_BIN, MA_JIAQI, LotteryManager
from lottery_system.services.prize_manager import PrizeManager

BANNER = "=" * 60 + "\n  Company Team Building Smart Lottery System\n" + "=" * 60

MAIN_MENU = """
---------------- Main Menu ----------------
1. Load participant list
2. View department groups
3. Prize settings
4. Start lottery
5. View winners
6. Export winner list to txt
0. Exit
-------------------------------------------"""

PRIZE_MENU = """
---------------- Prize Settings ----------------
a. View prizes
b. Load default prize library
c. Add custom prize
d. Reorder prizes
0. Back
------------------------------------------------"""


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    """Interactive controller for the whole lottery workflow."""

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.completed_prizes: set[str] = set()

    # ----- helpers ------------------------------------------------------

    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            raw = self._ask(prompt)
            try:
                value = int(raw)
                if value >= 1:
                    return value
            except ValueError:
                pass
            print("Please enter a positive integer.")

    def _confirm_remove_or_terminate(self, kind: str) -> bool:
        while True:
            choice = self._ask(f"[R] Remove {kind} data and continue / [T] Terminate upload: ").lower()
            if choice == "r":
                return True
            if choice == "t":
                return False
            print("Please enter R or T.")

    # ----- main loop ----------------------------------------------------

    def run(self) -> None:
        print(BANNER)
        while True:
            print(MAIN_MENU)
            choice = self._ask("Select an option: ")
            try:
                if choice == "1":
                    self.load_participants()
                elif choice == "2":
                    self.view_groups()
                elif choice == "3":
                    self.prize_settings()
                elif choice == "4":
                    self.start_lottery()
                elif choice == "5":
                    self.show_winners()
                elif choice == "6":
                    self.export_results()
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Invalid option, please try again.")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

    # ----- list management ---------------------------------------------

    def load_participants(self) -> None:
        print("1. Built-in default team building list")
        print("2. Custom txt file (each line: Name,Department Group)")
        choice = self._ask("Choose list source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip('"').strip("'")
            if not path:
                print("No path given.")
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid choice.")
            return

        if errors:
            print(f"Found {len(errors)} invalid entr{'y' if len(errors) == 1 else 'ies'}:")
            for error in errors:
                print(f"  {error}")
            if not self._confirm_remove_or_terminate("invalid"):
                print("Upload terminated.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  {user.name} ({user.department})")
            if not self._confirm_remove_or_terminate("duplicate"):
                print("Upload terminated.")
                return

        if not valid:
            print("No valid participants were loaded.")
            return

        self.users = valid
        self.lottery = None
        self.completed_prizes = set()
        print(f"Loaded {len(valid)} participant(s). Previous lottery results were reset.")

    def view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {department}: {count} people")
        print(f"Total: {len(self.users)} people")

    # ----- prize management --------------------------------------------

    def prize_settings(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ").lower()
            if choice == "a":
                self.view_prizes()
            elif choice == "b":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    print("Some default prizes could not be added:")
                    for error in errors:
                        print(f"  {error}")
                else:
                    print("Default prize library loaded.")
            elif choice == "c":
                self.add_custom_prize()
            elif choice == "d":
                self.reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                  f"lottery person: {prize.associated_drawer or 'None'} | "
                  f"avoid groups: {', '.join(prize.avoid_groups) or 'None'}")

    def _choose_avoid_groups(self) -> list[str]:
        if not self.users:
            print("No participant list loaded; no avoidance groups can be selected.")
            return []
        info = self.list_manager.get_group_info(self.users)
        groups = list(info.keys())
        print("Available groups:")
        for index, department in enumerate(groups, start=1):
            print(f"  {index}. {department}")
        raw = self._ask("Avoidance groups (numbers or names, comma-separated; Enter for none): ")
        selected: list[str] = []
        for token in [t.strip() for t in raw.split(",") if t.strip()]:
            if token.isdigit() and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
            else:
                name = next((g for g in groups if g.lower() == token.lower()), token)
                if name == token and token not in groups:
                    print(f"  Warning: '{token}' is not a current group name; kept anyway.")
            if name not in selected:
                selected.append(name)
        return selected

    def add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self._ask("Associated lottery person (Enter to skip): ") or None
        groups = self._choose_avoid_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize added: {prize.name} (quantity {prize.quantity}).")
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.view_prizes()
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery order updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery ------------------------------------------------------

    def _describe_rules(self, prize: Prize) -> str:
        if prize.associated_drawer is None:
            base = "Lottery person: not specified. Rule: previous winners excluded"
        else:
            base = f"Lottery person: {prize.associated_drawer}. "
            if prize.associated_drawer.strip().lower() == LI_BIN.lower():
                base += "Rule: previous winners excluded only (avoidance groups not applied)"
            elif self.lottery is not None and self.lottery.fallback_active(prize):
                base += "Rule: Cheng Ru Group protection active - only Cheng Ru Group members eligible"
            elif prize.associated_drawer.strip().lower() == MA_JIAQI.lower() and not prize.avoid_groups:
                base += "Rule: previous winners excluded"
            else:
                base += "Rule: previous winners excluded"
        if prize.avoid_groups and not (
            prize.associated_drawer and prize.associated_drawer.strip().lower() == LI_BIN.lower()
        ):
            base += f"; avoid groups: {', '.join(prize.avoid_groups)}"
        return base

    def _wait_until_resumed(self) -> bool:
        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
        while True:
            command = self._ask("> ").lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Please type 'continue' or 'terminate'.")

    def _run_round(self, prize: Prize) -> None:
        lottery = self.lottery
        lottery.start_round(prize)
        print(f"Prize: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._describe_rules(prize)}")
        print("Commands: Enter = draw next | pause | terminate")

        drawn = 0
        while drawn < prize.quantity:
            command = self._ask(
                f"[{ordinal(drawn + 1)} winner] Press Enter to draw (pause / terminate): "
            ).lower()
            if command == "terminate":
                print("Round terminated manually; remaining winners skipped.")
                break
            if command == "pause":
                if not self._wait_until_resumed():
                    print("Round terminated manually; remaining winners skipped.")
                    break
                continue
            if command == "continue":
                print("Lottery is not paused.")
                continue
            if command:
                print("Unknown command.")
                continue

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = lottery.draw_next()
            if user is None:
                print("No eligible participants remain for this prize; round ends early.")
                break
            drawn += 1
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        winners = lottery.finish_round()
        print(f"Round finished: {len(winners)} of {prize.quantity} winner(s) drawn.")
        for index, user in enumerate(winners, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    def start_lottery(self) -> None:
        if not self.users:
            print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please set up prizes first.")
            return
        pending = [prize for prize in prizes if prize.name not in self.completed_prizes]
        if not pending:
            print("All prizes have already been drawn.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)

        print(f"Starting lottery with {len(pending)} round(s).")
        for index, prize in enumerate(pending, start=1):
            print(f"\n########## Round {index}/{len(pending)} ##########")
            self._run_round(prize)
            self.completed_prizes.add(prize.name)

        print("\nAll rounds completed. Winner summary:")
        self.show_winners()

    # ----- results ------------------------------------------------------

    def show_winners(self) -> None:
        if self.lottery is None:
            print("No lottery results yet.")
            return
        grouped = self.lottery.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        for prize_name, winners in grouped.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.user.name} ({winner.user.department})")

    def export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export.")
            return
        _, message = (True, "")
        success, message = self.lottery.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    LotterySystemCLI().run()
