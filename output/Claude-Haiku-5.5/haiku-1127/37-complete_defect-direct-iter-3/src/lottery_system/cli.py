"""Command-line interaction for the lottery system."""

import time

from lottery_system.models import Prize, User, normalize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    """Format an integer as an English ordinal (1st, 2nd, 11th, ...)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    MENU = [
        "1. Load built-in team building list",
        "2. Upload custom txt list",
        "3. View department groups",
        "4. Load preset prizes",
        "5. Add custom prize",
        "6. Configure avoidance groups for a prize",
        "7. View prize list",
        "8. Reorder prize sequence",
        "9. Start lottery",
        "10. View winner results",
        "11. Export winner results (CSV)",
        "0. Exit",
    ]

    def __init__(self, draw_delay: float = 0.5) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.result_manager = ResultManager()
        self.last_prizes: list[Prize] = []
        self.draw_delay = draw_delay

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        try:
            while True:
                self._print_menu()
                choice = input("Select an option: ").strip()
                if choice == "0":
                    print("Goodbye!")
                    return
                handler = self._handlers().get(choice)
                if handler is None:
                    print("Invalid option, please try again.")
                    continue
                handler()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting lottery system.")

    def _handlers(self) -> dict:
        return {
            "1": self.load_default_list,
            "2": self.upload_custom_list,
            "3": self.view_groups,
            "4": self.load_preset_prizes,
            "5": self.add_custom_prize,
            "6": self.configure_avoid_groups,
            "7": self.view_prizes,
            "8": self.reorder_prizes,
            "9": self.start_lottery,
            "10": self.view_results,
            "11": self.export_results,
        }

    def _print_menu(self) -> None:
        print()
        print("\n".join(self.MENU))

    # ----- list management -----------------------------------------------
    def load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        if errors:
            self._print_errors(errors)
        self.users = users
        print(f"Built-in list loaded: {len(users)} participants.")

    def upload_custom_list(self) -> None:
        path = input("Enter the path of the txt file: ").strip().strip('"')
        if not path:
            print("Upload cancelled.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        valid, duplicates = self.list_manager.validate_users(users)

        if errors:
            print("Problems found in the file:")
            self._print_errors(errors)
        if duplicates:
            print("Duplicate names found (later occurrences):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")

        if errors or duplicates:
            print("  [r] remove invalid / duplicate data and keep the valid entries")
            print("  [c] terminate upload")
            decision = input("Choose r or c: ").strip().lower()
            if decision != "r":
                print("Upload terminated. Current list unchanged.")
                return
            users = valid

        if not users:
            print("No valid participants found. Current list unchanged.")
            return
        self.users = users
        print(f"Custom list loaded: {len(users)} participants.")

    def view_groups(self) -> None:
        if not self.users:
            print("No participants loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in info.items():
            print(f"  - {group}: {count} people")

    # ----- prize configuration -------------------------------------------
    def load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            self._print_errors(errors)
        else:
            print("Preset prizes loaded.")

    def add_custom_prize(self) -> None:
        name = input("Prize name: ").strip()
        try:
            quantity = int(input("Quantity: ").strip())
        except ValueError:
            print("Quantity must be a whole number.")
            return
        drawer = input("Associated lottery person (Enter for none): ").strip() or None
        groups = self._select_groups()
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize '{name}' added.")

    def configure_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        self._show_prizes(prizes)
        try:
            index = int(input("Select prize number: ").strip())
        except ValueError:
            print("Invalid number.")
            return
        if not 1 <= index <= len(prizes):
            print("Invalid number.")
            return
        prize = prizes[index - 1]
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoidance groups for '{prize.name}' updated.")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        self._show_prizes(prizes)

    def reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        self._show_prizes(prizes)
        raw = input("Enter new order as serial numbers (e.g. '3 1 2'): ").strip()
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(t) for t in tokens]
        except ValueError:
            print("Order must contain only serial numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
        else:
            print(f"Invalid order. Provide each number from 1 to {len(prizes)} exactly once.")

    def _show_prizes(self, prizes: list[Prize]) -> None:
        lm = LotteryManager(self.users)
        print("Prize sequence:")
        for i, prize in enumerate(prizes, 1):
            drawer = prize.associated_drawer or "None"
            print(f"  {i}. {prize.name} | Quantity: {prize.quantity} | Drawer: {drawer}")
            print(f"     Rule: {lm.describe_rules(prize)}")

    def _select_groups(self) -> list[str]:
        """Let the user pick one or more department groups (numbers or names)."""
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if not groups:
            print("No department groups available; no avoidance groups will be set.")
            return []
        print("Available groups:")
        for i, group in enumerate(groups, 1):
            print(f"  {i}. {group}")
        while True:
            raw = input("Select avoidance groups (numbers or names, comma-separated; Enter for none): ").strip()
            if not raw:
                return []
            selected: list[str] = []
            unknown: list[str] = []
            for token in raw.split(","):
                item = token.strip()
                if not item:
                    continue
                if item.isdigit() and 1 <= int(item) <= len(groups):
                    match = groups[int(item) - 1]
                else:
                    match = next((g for g in groups if normalize(g) == normalize(item)), None)
                if match is None:
                    unknown.append(item)
                elif match not in selected:
                    selected.append(match)
            if unknown:
                print(f"Unknown group(s): {', '.join(unknown)}. Please try again.")
                continue
            return selected

    # ----- lottery -------------------------------------------------------
    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lm = LotteryManager(self.users)
        rm = ResultManager()
        self.result_manager = rm
        self.last_prizes = prizes

        print("\n=== Lottery begins ===")
        for round_no, prize in enumerate(prizes, 1):
            print(f"\n--- Round {round_no}: {prize.name} ---")
            print(f"Quantity: {prize.quantity}")
            print(f"Rule: {lm.describe_rules(prize)}")
            winners = self._run_round(lm, rm, prize)
            lm.finish_round(prize, winners)
            if winners:
                print(f"Round {round_no} results:")
                for i, user in enumerate(winners, 1):
                    print(f"  {i}. {user.name} ({user.department})")
            else:
                print(f"Round {round_no} produced no winners.")

        print("\n=== Lottery finished ===")
        self._print_results(prizes, rm)

    def _run_round(self, lm: LotteryManager, rm: ResultManager, prize: Prize) -> list[User]:
        winners: list[User] = []
        for index in range(1, prize.quantity + 1):
            if not lm._get_eligible_pool(prize):
                print("No eligible candidates remain for this prize. Round ends.")
                break
            action = self._await_action()
            if action == "terminate":
                print("Round terminated. Remaining draws for this prize are skipped.")
                break
            print(f"Currently drawing the {ordinal(index)} winner...")
            time.sleep(self.draw_delay)
            user = lm.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize. Round ends.")
                break
            winners.append(user)
            rm.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        return winners

    def _await_action(self) -> str:
        """Wait for operator command before the next draw. Returns 'draw' or 'terminate'."""
        while True:
            cmd = input("[Enter] draw next | 'pause' | 'terminate': ").strip().lower()
            if cmd == "":
                return "draw"
            if cmd == "terminate":
                return "terminate"
            if cmd == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    sub = input("(paused) > ").strip().lower()
                    if sub == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if sub == "terminate":
                        return "terminate"
                    print("Please type 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # ----- results -------------------------------------------------------
    def view_results(self) -> None:
        if not self.result_manager.get_all_winners():
            print("No lottery results yet.")
            return
        self._print_results(self.last_prizes, self.result_manager)

    def _print_results(self, prizes: list[Prize], rm: ResultManager) -> None:
        grouped = rm.get_winners_by_prize(prizes)
        print("Winner list:")
        for prize in prizes:
            print(f"\n{prize.name}:")
            winners = grouped.get(prize.name, [])
            if not winners:
                print("  (no winners)")
            for w in winners:
                print(f"  - {w.user.name} ({w.user.department})")

    def export_results(self) -> None:
        if not self.last_prizes or not self.result_manager.get_all_winners():
            print("No lottery results to export. Run the lottery first.")
            return
        _, message = self.result_manager.export_to_csv(self.last_prizes)
        print(message)

    # ----- utilities -----------------------------------------------------
    @staticmethod
    def _print_errors(errors: list[str]) -> None:
        for error in errors:
            print(f"  ! {error}")


def main() -> None:
    LotteryCLI().run()
