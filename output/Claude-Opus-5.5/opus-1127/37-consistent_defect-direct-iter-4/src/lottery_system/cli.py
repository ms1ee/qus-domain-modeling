from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.lottery = None

    def _set_users(self, users):
        if self.lottery and self.lottery.result_manager.winners:
            ans = input("Loading a new list resets lottery results. Continue? (y/n): ").strip().lower()
            if ans != "y":
                print("Load cancelled.")
                return
        self.users = users
        self.lottery = LotteryManager(users)
        print(f"{len(users)} participants loaded.")

    def _handle_loaded(self, users, errors):
        if errors:
            print("Problems detected:")
            for e in errors:
                print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        if errors or dups:
            while True:
                c = input("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").strip().lower()
                if c == "r":
                    break
                if c == "t":
                    print("Upload terminated.")
                    return
        if not valid:
            print("No valid participants found.")
            return
        self._set_users(valid)

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._handle_loaded(users, errors)

    def load_custom(self):
        path = input("Enter txt file path: ").strip()
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
        print("Groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print(e)
        print("Preset prizes loaded.")

    def add_prize(self):
        name = input("Prize name: ").strip()
        qty = input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = input("Avoidance groups (numbers separated by commas, blank for none): ").strip()
            for s in sel.replace("，", ",").split(","):
                s = s.strip()
                if not s:
                    continue
                if s.isdigit() and 1 <= int(s) <= len(groups):
                    avoid.append(groups[int(s) - 1])
                else:
                    print(f"Ignored invalid selection: {s}")
        drawer = input("Associated lottery person (blank for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{p.name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def list_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            av = ", ".join(p.avoid_groups) or "None"
            print(f"  {i}. {p.name} x{p.quantity} | avoid: {av} | drawer: {p.associated_drawer or 'None'}")

    def reorder(self):
        self.list_prizes()
        if not self.prize_manager.get_prizes():
            return
        s = input("Enter new order as serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in s.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.list_prizes()
        else:
            print("Invalid order.")

    def start(self):
        if not self.users or self.lottery is None:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        for p in prizes:
            self.lottery.run_round(p)
        print("All rounds completed.")
        self.summary()

    def summary(self):
        if self.lottery is None or not self.lottery.result_manager.winners:
            print("No winners yet.")
            return
        print("=== Complete Winner List ===")
        for name, ws in self.lottery.result_manager.get_summary(self.prize_manager.get_prizes()):
            if not ws:
                continue
            print(f"[{name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {w.time.strftime('%Y-%m-%d %H:%M:%S')}")

    def export(self):
        if self.lottery is None:
            print("No winners to export.")
            return
        ok, msg = self.lottery.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.list_prizes,
            "7": self.reorder, "8": self.start, "9": self.summary, "10": self.export,
        }
        while True:
            print("\n==== Team Building Smart Lottery ====")
            print("1. Load default list      2. Upload custom list")
            print("3. View groups            4. Load preset prizes")
            print("5. Add custom prize       6. View prizes")
            print("7. Reorder prizes         8. Start lottery")
            print("9. View summary          10. Export results")
            print("0. Exit")
            try:
                c = input("Choose: ").strip()
            except EOFError:
                break
            if c == "0":
                break
            act = actions.get(c)
            if act:
                try:
                    act()
                except EOFError:
                    break
            else:
                print("Invalid choice.")
        print("Goodbye!")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
