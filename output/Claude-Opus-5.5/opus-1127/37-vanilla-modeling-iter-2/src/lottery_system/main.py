"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.result_manager import ResultManager


class LotterySystem:
    def __init__(self, input_func=input, output_func=print):
        self.inp = input_func
        self.out = output_func
        self.status = "idle"
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery_manager = None

    def ask(self, prompt):
        try:
            return self.inp(prompt).strip()
        except EOFError:
            return "0"

    # ----------------------------------------------------------- list handling
    def _accept_list(self, users, errors):
        for e in errors:
            self.out(f"  [!] {e}")
        valid, dups = self.list_manager.validate_users(users)
        for d in dups:
            self.out(f"  [!] Duplicate name: {d.name} ({d.department})")
        if errors or dups:
            choice = self.ask("Invalid data found. (r)emove invalid data and continue, "
                              "or (t)erminate upload? [r/t]: ").lower()
            if choice.startswith("t"):
                self.out("Upload terminated. Current list unchanged.")
                return
        if not valid:
            self.out("No valid participants loaded.")
            return
        self.users = valid
        self.lottery_manager = None
        self.out(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        self._accept_list(*self.list_manager.load_default_list())

    def load_custom(self):
        path = self.ask("Enter txt file path: ")
        self._accept_list(*self.list_manager.load_custom_list(path))

    def show_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            self.out("No list loaded.")
            return
        self.out("Department groups:")
        for g, c in info.items():
            self.out(f"  {g}: {c} people")

    # ---------------------------------------------------------- prize handling
    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            self.out(f"  [!] {e}")
        self.out("Preset prizes loaded.")

    def add_prize(self):
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            self.out("Available groups: " + ", ".join(f"{i}.{g}" for i, g in enumerate(groups, 1)))
        raw = self.ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        avoid = []
        for item in raw.replace("\uff0c", ",").split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit() and 1 <= int(item) <= len(groups):
                avoid.append(groups[int(item) - 1])
            else:
                avoid.append(item)
        drawer = self.ask("Associated lottery person (blank for none): ") or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            self.out("Prize added.")
        except ValueError as e:
            self.out(f"  [!] {e}")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            self.out(f"  {i}. {p}")

    def reorder(self):
        self.show_prizes()
        raw = self.ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            self.out("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Prizes reordered.")
            self.show_prizes()
        else:
            self.out("Invalid order.")

    # ----------------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.users:
            self.out("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("Please configure prizes first.")
            return
        if self.lottery_manager is None:
            self.lottery_manager = LotteryManager(self.users, self.result_manager)
        self.status = "running"
        for i, p in enumerate(prizes, 1):
            self.lottery_manager.run_round(p, i, self.inp, self.out)
        self.status = "finished"
        self.out("All rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        self.out("====== Complete Winner List ======")
        any_w = False
        for name, ws in data.items():
            if not ws:
                continue
            any_w = True
            self.out(f"[{name}]")
            for w in ws:
                self.out(f"  {w.user.name} ({w.user.department}) - {name} - "
                         f"{w.time.strftime('%Y-%m-%d %H:%M:%S')}")
        if not any_w:
            self.out("No winners yet.")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.out(msg)

    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.show_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.show_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_summary,
            "10": self.export,
        }
        while True:
            self.out("\n===== Team Building Smart Lottery =====")
            self.out("1. Load default list      2. Upload custom list   3. View groups")
            self.out("4. Load preset prizes     5. Add custom prize     6. View prizes")
            self.out("7. Reorder prizes         8. Start lottery        9. Show results")
            self.out("10. Export results        0. Exit")
            c = self.ask("Choose: ")
            if c == "0":
                self.out("Goodbye.")
                break
            fn = actions.get(c)
            if fn:
                fn()
            else:
                self.out("Invalid choice.")


def main():
    LotterySystem().run()


if __name__ == "__main__":
    main()
