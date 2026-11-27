"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    def ask(self, prompt):
        try:
            return input(prompt)
        except EOFError:
            raise SystemExit(0)

    # ---------------------------------------------------------------- lists
    def _accept_list(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Problems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate name: {d.name} ({d.department})")
            choice = self.ask("Remove invalid data and continue (r) or terminate upload (t)? ").strip().lower()
            if choice != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid users loaded.")
            return
        self.users = valid
        self.lottery = None
        self.result_manager = ResultManager()
        print(f"Loaded {len(valid)} valid users.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def load_custom(self):
        path = self.ask("Enter txt file path (each line: Name,Department): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("Upload failed.")
            return
        self._accept_list(users, errors)

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Current groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # --------------------------------------------------------------- prizes
    def _select_groups(self):
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = self.ask("Avoidance groups (numbers or names, comma-separated, blank for none): ").strip()
        result = []
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                result.append(groups[int(part) - 1])
            else:
                result.append(part)
        return result

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Default prizes loaded.")

    def add_prize(self):
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        groups = self._select_groups()
        drawer = self.ask("Associated drawer (blank for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, groups, drawer)
            print(f"Added: {p}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_avoid(self):
        prizes = self.view_prizes()
        if not prizes:
            return
        raw = self.ask("Select prize number: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            print("Invalid selection.")
            return
        prize = prizes[int(raw) - 1]
        self.prize_manager.set_avoid_groups(prize.name, self._select_groups())
        print(f"Updated: {prize}")

    def reorder(self):
        prizes = self.view_prizes()
        if not prizes:
            return
        raw = self.ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            order = []
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.view_prizes()
        else:
            print("Invalid order.")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")
        return prizes

    # -------------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        for prize in prizes:
            self.lottery.run_round(prize, input_func=self.ask, output=print,
                                   on_winner=self.result_manager.add_winner)
        print("All rounds completed.")
        self.show_results()

    def show_results(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("===== Complete Winner List =====")
        any_w = False
        for name, winners in grouped.items():
            if not winners:
                continue
            any_w = True
            print(f"[{name}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {name}")
        if not any_w:
            print("No winners yet.")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prizes", self.load_default_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("Configure prize avoidance groups", self.configure_avoid),
            "7": ("Reorder prizes", self.reorder),
            "8": ("View prizes", self.view_prizes),
            "9": ("Start lottery", self.start_lottery),
            "10": ("View results", self.show_results),
            "11": ("Export results", self.export),
            "0": ("Exit", None),
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            for k, (label, _) in actions.items():
                print(f"  {k}. {label}")
            choice = self.ask("Select: ").strip()
            if choice == "0":
                print("Bye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid choice.")
                continue
            action[1]()


def main():
    try:
        LotteryApp().run()
    except (KeyboardInterrupt, SystemExit):
        print("\nExiting.")


if __name__ == "__main__":
    main()
