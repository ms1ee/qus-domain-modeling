"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "0"


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager = None

    # ------------------------------------------------------------- list
    def _handle_loaded(self, users, errors) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            print("Validation problems detected:")
            for e in errors:
                print("  " + e)
            for d in duplicates:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = _ask("Remove invalid data and continue (r) or terminate upload (t)? ").lower()
            if choice != "r":
                print("Upload terminated. Current list unchanged.")
                return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        self.result_manager = ResultManager()
        self.lottery_manager = None
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._handle_loaded(users, errors)

    def load_custom(self):
        path = _ask("Enter txt file path (each line 'Name,Department Group'): ")
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print(e)
            return
        self._handle_loaded(users, errors)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # ------------------------------------------------------------- prizes
    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            raw = _ask("Select avoidance groups by number or name (comma separated, empty for none): ")
        else:
            raw = _ask("Enter avoidance group names (comma separated, empty for none): ")
        selected = []
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                selected.append(groups[int(part) - 1])
            else:
                selected.append(part)
        return selected

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def add_prize(self):
        name = _ask("Prize name: ")
        qty = _ask("Quantity: ")
        drawer = _ask("Associated lottery person (empty for none): ") or None
        groups = self._select_groups()
        try:
            self.prize_manager.add_prize(name, qty, groups, drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def list_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return False
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")
        return True

    def set_avoid_groups(self):
        if not self.list_prizes():
            return
        idx = _ask("Select prize number: ")
        if not idx.isdigit():
            print("Invalid number.")
            return
        groups = self._select_groups()
        if self.prize_manager.set_avoid_groups(int(idx) - 1, groups):
            print("Avoidance groups updated.")
        else:
            print("Invalid prize number.")

    def reorder(self):
        if not self.list_prizes():
            return
        raw = _ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated:")
            self.list_prizes()
        else:
            print("Invalid order; must be a permutation of all serial numbers.")

    # ------------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery_manager is None:
            self.lottery_manager = LotteryManager(self.users, self.result_manager)
        for n, prize in enumerate(prizes, 1):
            self.lottery_manager.run_round(prize, n)
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("===== Complete Winner List =====")
        any_w = False
        for pname, winners in grouped.items():
            for w in winners:
                any_w = True
                print(f"  {w.user.name} | {w.user.department} | {pname}")
        if not any_w:
            print("  No winners yet.")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ------------------------------------------------------------- loop
    def run(self):
        actions = {
            "1": self.load_default,
            "2": self.load_custom,
            "3": self.view_groups,
            "4": self.load_default_prizes,
            "5": self.add_prize,
            "6": self.set_avoid_groups,
            "7": self.list_prizes,
            "8": self.reorder,
            "9": self.start_lottery,
            "10": self.show_results,
            "11": self.export,
        }
        while True:
            print(
                "\n=== Team Building Smart Lottery ===\n"
                " 1. Load default list\n 2. Upload custom list\n 3. View groups\n"
                " 4. Load preset prizes\n 5. Add custom prize\n 6. Set prize avoidance groups\n"
                " 7. View prizes\n 8. Reorder prizes\n 9. Start lottery\n"
                "10. View winner list\n11. Export results\n 0. Exit"
            )
            choice = _ask("Choose: ")
            if choice == "0":
                print("Goodbye.")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice.")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
