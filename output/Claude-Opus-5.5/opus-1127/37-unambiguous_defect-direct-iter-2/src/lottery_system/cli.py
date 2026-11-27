"""Command-line interface."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class LotteryCLI:
    def __init__(self, input_func=input, output=print):
        self.input = input_func
        self.out = output
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_done = False

    def ask(self, prompt: str) -> str:
        try:
            return self.input(prompt)
        except EOFError:
            return "0"

    def run(self):
        actions = {
            "1": self.load_default_list, "2": self.upload_list, "3": self.view_groups,
            "4": self.load_default_prizes, "5": self.add_prize, "6": self.view_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_results,
            "10": self.export,
        }
        while True:
            self.out("\n===== Team Building Smart Lottery System =====")
            self.out("1. Load default list        2. Upload custom txt list")
            self.out("3. View groups              4. Load preset prizes")
            self.out("5. Add custom prize         6. View prizes")
            self.out("7. Reorder prizes           8. Start lottery")
            self.out("9. Show results             10. Export results")
            self.out("0. Exit")
            choice = self.ask("Select: ").strip()
            if choice == "0":
                self.out("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                self.out("Invalid choice.")

    def _apply_list(self, users, errors) -> None:
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            for e in errors:
                self.out(e)
            for d in dups:
                self.out(f"Duplicate name: {d.name} ({d.department})")
            while True:
                c = self.ask("Remove invalid data and continue (r) or terminate upload (t)? ").strip().lower()
                if c == "r":
                    break
                if c == "t":
                    self.out("Upload terminated.")
                    return
        if not valid:
            self.out("No valid participants loaded.")
            return
        self.users = valid
        self.out(f"Loaded {len(valid)} valid participants.")

    def load_default_list(self):
        self._apply_list(*self.list_manager.load_default_list())

    def upload_list(self):
        path = self.ask("Path of txt list (format per line: Name,Department): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors and errors[0].startswith(("File not found", "Unable")):
            self.out(errors[0])
            return
        self._apply_list(users, errors)

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            self.out("No list loaded.")
            return
        for i, (g, c) in enumerate(info.items(), 1):
            self.out(f"{i}. {g}: {c} people")

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            self.out(e)
        self.view_prizes()

    def add_prize(self):
        name = self.ask("Prize name: ").strip()
        qty = self.ask("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                self.out(f"{i}. {g}")
        raw = self.ask("Avoidance groups (numbers or names, comma-separated, blank for none): ").strip()
        avoid = []
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                avoid.append(groups[int(part) - 1])
            else:
                avoid.append(part)
        drawer = self.ask("Associated lottery person (blank for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            self.out(f"Prize added: {p.name} x{p.quantity}")
        except ValueError as exc:
            self.out(f"Error: {exc}")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            self.out(f"{i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def reorder(self):
        self.view_prizes()
        raw = self.ask("New order (serial numbers separated by space/comma): ")
        try:
            order = [int(x) for x in raw.replace(",", " ").split()]
        except ValueError:
            self.out("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Prizes reordered.")
            self.view_prizes()
        else:
            self.out("Invalid order; it must be a permutation of current serial numbers.")

    def start_lottery(self):
        if not self.users:
            self.out("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("Please configure prizes first.")
            return
        self.result_manager = ResultManager()
        lm = LotteryManager(self.users, self.result_manager)
        lm.run_all(prizes, self.ask, self.out)
        self.lottery_done = True
        self.out("\nAll rounds completed.")
        self.show_results()

    def show_results(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.winners:
            self.out("No winners yet.")
            return
        self.out("===== Complete Winner List =====")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self.out(f"[{prize_name}]")
            for w in winners:
                self.out(f"  {w.user.name} ({w.user.department}) - {prize_name}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.out(msg)


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
