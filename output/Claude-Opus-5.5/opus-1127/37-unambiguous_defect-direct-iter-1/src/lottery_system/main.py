"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.lottery = None
        self.results = ResultManager()

    # ---- helpers ----
    @staticmethod
    def ask(prompt):
        try:
            return input(prompt).strip()
        except EOFError:
            return "0"

    def _set_users(self, users):
        self.users = users
        self.lottery = LotteryManager(users)
        self.results = ResultManager()
        print(f"Loaded {len(users)} valid participants.")

    def _process_loaded(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        if not errors and not dups:
            self._set_users(valid)
            return
        if errors:
            print("Format errors detected:")
            for e in errors:
                print("  " + e)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        choice = self.ask("Type 'r' to remove invalid data and continue, "
                          "or 't' to terminate upload: ").lower()
        if choice == "r":
            self._set_users(valid)
        else:
            print("Upload terminated.")

    # ---- actions ----
    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._process_loaded(users, errors)

    def upload_custom(self):
        path = self.ask("Enter path of txt list (format per line: Name,Department): ")
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            choice = self.ask("No valid data. Press Enter to return.")
            return
        self._process_loaded(users, errors)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Valid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) if p.avoid_groups else "None"
            print(f"  {i}. {p.name} x{p.quantity} | Drawer: {p.associated_drawer or 'N/A'}"
                  f" | Avoid: {avoid}")

    def load_presets(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        self.show_prizes()

    def _select_groups(self):
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = self.ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        selected = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                g = groups[int(token) - 1]
            else:
                g = token
            if g not in selected:
                selected.append(g)
        return selected

    def add_custom_prize(self):
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        drawer = self.ask("Associated lottery person (blank for none): ") or None
        groups = self._select_groups()
        try:
            p = self.prize_manager.add_prize(name, qty, groups, drawer)
            print(f"Prize added: {p.name}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_avoidance(self):
        self.show_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        idx = self.ask("Prize number: ")
        if not idx.isdigit() or not 1 <= int(idx) <= len(prizes):
            print("Invalid prize number.")
            return
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(int(idx) - 1, groups)
        print("Avoidance groups updated.")

    def reorder(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = self.ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.show_prizes()
        else:
            print("Invalid order; must be a permutation of current serial numbers.")

    def start_lottery(self):
        if not self.users or self.lottery is None:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        for p in prizes:
            self.lottery.run_round(p, result_manager=self.results)
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        grouped = self.results.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        any_w = False
        for name, ws in grouped.items():
            if not ws:
                continue
            any_w = True
            print(f"[{name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {name}")
        if not any_w:
            print("  (no winners yet)")

    def export(self):
        ok, msg = self.results.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        menu = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.upload_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prizes", self.load_presets),
            "5": ("Add custom prize", self.add_custom_prize),
            "6": ("Configure avoidance groups", self.configure_avoidance),
            "7": ("Reorder prizes", self.reorder),
            "8": ("View prizes", self.show_prizes),
            "9": ("Start lottery", self.start_lottery),
            "10": ("Show winner summary", self.show_summary),
            "11": ("Export results", self.export),
        }
        print("=== Team Building Smart Lottery System ===")
        while True:
            print()
            for k, (label, _) in menu.items():
                print(f"{k}. {label}")
            print("0. Exit")
            choice = self.ask("Select: ")
            if choice == "0":
                print("Goodbye.")
                break
            item = menu.get(choice)
            if item:
                item[1]()
            else:
                print("Invalid option.")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
