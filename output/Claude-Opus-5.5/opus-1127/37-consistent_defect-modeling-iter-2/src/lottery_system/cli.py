"""Command-line interface."""
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MENU = """
======== Team Building Smart Lottery ========
1. Load default participant list
2. Upload custom participant list (txt)
3. View department groups
4. Load preset prize library
5. Add custom prize
6. View / reorder prizes
7. Start lottery
8. Show summary of winners
9. Export results
0. Exit
"""


class App:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    def _set_users(self, users):
        self.users = users
        self.result_manager = ResultManager()
        self.lottery = LotteryManager(users, self.result_manager)

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        self._set_users(valid)
        print(f"Default list loaded: {len(valid)} participants.")

    def load_custom(self):
        path = input("Enter txt file path: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        for e in errors:
            print("  " + e)
        for d in dups:
            print(f"  Duplicate name: {d.name} ({d.department})")
        if not valid:
            print("No valid participants loaded.")
            return
        if errors or dups:
            ch = input("Invalid data found. 'r' remove invalid data and continue, "
                       "'t' terminate upload: ").strip().lower()
            if ch != "r":
                print("Upload terminated.")
                return
        self._set_users(valid)
        print(f"Custom list loaded: {len(valid)} participants.")

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"{i}. {g}: {c} people")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"{i}. {p.name} x{p.quantity} | avoid: {', '.join(p.avoid_groups) or '-'} "
                  f"| drawer: {p.associated_drawer or '-'}")
        return prizes

    def add_prize(self):
        name = input("Prize name: ").strip()
        qty = input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = input("Avoidance groups (numbers separated by comma, empty for none): ").strip()
            for s in sel.replace("，", ",").split(","):
                s = s.strip()
                if s.isdigit() and 1 <= int(s) <= len(groups):
                    if groups[int(s) - 1] not in avoid:
                        avoid.append(groups[int(s) - 1])
                elif s:
                    print(f"  Ignored invalid selection: {s}")
        drawer = input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print("Prize added.")
        except ValueError as e:
            print(f"Error: {e}")

    def reorder(self):
        prizes = self.show_prizes()
        if not prizes:
            return
        s = input("New order (serial numbers separated by space/comma, empty to keep): ").strip()
        if not s:
            return
        parts = [p for p in s.replace(",", " ").split() if p]
        if self.prize_manager.reorder_prizes(parts):
            print("Prizes reordered.")
            self.show_prizes()
        else:
            print("Invalid order.")

    def start(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        for i, p in enumerate(prizes, 1):
            self.lottery.run_round(p, i)
        print("\nAll rounds completed.")
        self.summary()

    def summary(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n======== Winner Summary ========")
        any_w = False
        for nm, ws in grouped.items():
            for w in ws:
                any_w = True
                print(f"{w.user.name},{w.user.department},{nm},"
                      f"{w.time.strftime('%Y-%m-%d %H:%M:%S')}")
        if not any_w:
            print("(no winners)")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {"1": self.load_default, "2": self.load_custom, "3": self.view_groups,
                   "4": self._load_prizes, "5": self.add_prize, "6": self.reorder,
                   "7": self.start, "8": self.summary, "9": self.export}
        while True:
            print(MENU)
            try:
                ch = input("Choose: ").strip()
            except EOFError:
                break
            if ch == "0":
                break
            act = actions.get(ch)
            if act:
                try:
                    act()
                except EOFError:
                    break
            else:
                print("Invalid choice.")
        print("Bye.")

    def _load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print(e)
        print("Preset prizes loaded.")


def main():
    App().run()


if __name__ == "__main__":
    main()
