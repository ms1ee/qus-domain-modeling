"""Command-line interface."""
from lottery_system.models import SPECIAL_DRAWER
from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager, TIME_FMT

MENU = """
========== Team Building Smart Lottery ==========
 1. Load default participant list
 2. Upload custom participant list (txt)
 3. View department groups
 4. Load preset prizes
 5. Add custom prize
 6. View prizes
 7. Reorder prizes
 8. Start lottery
 9. View winner summary
10. Export results
 0. Exit
=================================================="""


def _input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        raise SystemExit(0)


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.lottery_manager = None
        self.users = []
        self.status = "idle"

    # ----- list -----
    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors, allow_terminate=False)

    def load_custom(self):
        path = _input("Enter txt file path: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print(e)
            print("No valid data loaded.")
            return
        self._accept_users(users, errors, allow_terminate=True)

    def _accept_users(self, users, errors, allow_terminate):
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Problems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            if allow_terminate:
                while True:
                    c = _input("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").strip().lower()
                    if c in ("r", "t"):
                        break
                if c == "t":
                    print("Upload terminated. Current list unchanged.")
                    return
            print("Invalid data removed.")
        self.users = valid
        self.lottery_manager = None
        print(f"Loaded {len(valid)} valid participants.")

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for g, c in info.items():
            print(f"  {g}: {c} people")

    # ----- prizes -----
    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print(e)
        print("Preset prizes loaded.")

    def add_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        avoid = []
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = _input("Avoidance groups (numbers or names, comma-separated, empty for none): ").strip()
        for item in raw.replace("\uff0c", ",").split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit() and 1 <= int(item) <= len(groups):
                avoid.append(groups[int(item) - 1])
            else:
                avoid.append(item)
        drawer = _input("Associated lottery person (empty for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{p.name}' added.")
        except ValueError as e:
            print(f"Error: {e}")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | avoid: {', '.join(p.avoid_groups) or 'none'}"
                  f" | drawer: {p.associated_drawer or 'none'}")

    def reorder(self):
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = _input("Enter new order as serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.view_prizes()
        else:
            print("Invalid order; must be a permutation of current serial numbers.")

    # ----- lottery -----
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
        self.status = "running"
        print("Commands during lottery: Enter = draw, 'pause', 'continue', 'terminate' (skip round).")
        for idx, prize in enumerate(prizes, 1):
            drawn = sum(1 for w in self.result_manager.winners if w.prize_name == prize.name)
            if drawn >= prize.quantity:
                continue
            print(f"\n----- Round {idx}: {prize.name} -----")
            print(f"Quantity: {prize.quantity}")
            print(f"Lottery person: {prize.associated_drawer or 'none'}"
                  + (" (special)" if prize.associated_drawer == SPECIAL_DRAWER else ""))
            print(f"Rules: {self.lottery_manager.get_rule_description(prize)}")
            winners = self.lottery_manager.run_round(prize, input, print)
            print(f"Round {idx} results:")
            if not winners:
                print("  (no winners)")
            for i, u in enumerate(winners, 1):
                print(f"  {i}. {u.name} ({u.department}) - {prize.name}")
        self.status = "finished"
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n========== Winner Summary ==========")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for pname, ws in grouped.items():
            print(f"[{pname}]")
            if not ws:
                print("  (none)")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {pname} - {w.time.strftime(TIME_FMT)}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.view_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_summary,
            "10": self.export,
        }
        while True:
            print(MENU)
            choice = _input("Select: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid choice.")
                continue
            action()


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
