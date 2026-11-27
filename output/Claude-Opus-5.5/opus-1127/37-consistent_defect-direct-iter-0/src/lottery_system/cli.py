"""Command-line interface for the lottery system."""

from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MENU = """
========== Team Building Smart Lottery ==========
 1. Load default list
 2. Upload custom list (txt)
 3. View group information
 4. Load preset prizes
 5. Add custom prize
 6. Configure avoidance groups for a prize
 7. Reorder prizes
 8. View prizes
 9. Start lottery
10. View complete winner list
11. Export results
 0. Exit
"""


class App:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.result_manager = ResultManager()

    def ask(self, prompt):
        try:
            return input(prompt)
        except EOFError:
            return "0"

    def groups(self):
        return list(self.list_manager.get_group_info(self.users).keys())

    def _accept(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        for e in errors:
            print(e)
        for d in dups:
            print(f"Duplicate name: {d.name} ({d.department})")
        if errors or dups:
            choice = self.ask(
                "Invalid data found. 'r' = remove invalid data and continue, "
                "'t' = terminate upload: "
            ).strip().lower()
            if choice != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid users loaded.")
            return
        self.users = valid
        self.list_manager.users = valid
        print(f"Loaded {len(valid)} valid participants.")

    def select_groups(self):
        groups = self.groups()
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = self.ask("Avoidance groups (numbers or names, comma separated, empty for none): ")
        result = []
        for token in raw.replace(";", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                result.append(groups[int(token) - 1])
            else:
                result.append(token)
        return result

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(
                f"  {i}. {p.name} x{p.quantity} | avoid: "
                f"{', '.join(p.avoid_groups) or 'none'} | drawer: "
                f"{p.associated_drawer or 'none'}"
            )

    def run(self):
        while True:
            print(MENU)
            c = self.ask("Select: ").strip()
            if c == "0":
                print("Bye.")
                return
            elif c == "1":
                self._accept(*self.list_manager.load_default_list())
            elif c == "2":
                path = self.ask("Path of txt list: ").strip().strip('"')
                self._accept(*self.list_manager.load_custom_list(path))
            elif c == "3":
                info = self.list_manager.get_group_info(self.users)
                if not info:
                    print("No list loaded.")
                for g, n in info.items():
                    print(f"  {g}: {n} people")
            elif c == "4":
                for e in self.prize_manager.load_default_prizes():
                    print(e)
                self.show_prizes()
            elif c == "5":
                name = self.ask("Prize name: ")
                qty = self.ask("Quantity: ")
                drawer = self.ask("Associated lottery person (empty for none): ").strip() or None
                groups = self.select_groups()
                try:
                    self.prize_manager.add_prize(name, qty, groups, drawer)
                    print("Prize added.")
                except ValueError as exc:
                    print(f"Error: {exc}")
            elif c == "6":
                self.show_prizes()
                idx = self.ask("Prize number: ").strip()
                if not idx.isdigit():
                    print("Invalid number.")
                    continue
                groups = self.select_groups()
                if self.prize_manager.set_avoid_groups(int(idx) - 1, groups):
                    print("Avoidance groups updated.")
                else:
                    print("Invalid prize number.")
            elif c == "7":
                self.show_prizes()
                raw = self.ask("New order (e.g. 3,2,1): ")
                try:
                    order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
                except ValueError:
                    order = []
                print("Reordered." if self.prize_manager.reorder_prizes(order) else "Invalid order.")
            elif c == "8":
                self.show_prizes()
            elif c == "9":
                prizes = self.prize_manager.get_prizes()
                if not self.users or not prizes:
                    print("Please load a list and configure prizes first.")
                    continue
                self.result_manager = ResultManager()
                lm = LotteryManager(self.users)
                for p in prizes:
                    lm.run_round(p, self.result_manager, input_func=self.ask)
                print(self.result_manager.format_summary(prizes))
            elif c == "10":
                print(self.result_manager.format_summary(self.prize_manager.get_prizes()))
            elif c == "11":
                ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
                print(msg)
            else:
                print("Invalid option.")


def main():
    App().run()


if __name__ == "__main__":
    main()
