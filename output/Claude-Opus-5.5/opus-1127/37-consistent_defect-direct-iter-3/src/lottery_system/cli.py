"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    def _set_users(self, users, errors):
        for e in errors:
            print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        for d in dups:
            print(f"  Duplicate name: {d.name} ({d.department})")
        if errors or dups:
            ans = input("Invalid data found. [r]emove invalid data and continue / [t]erminate upload: ").strip().lower()
            if ans.startswith("t"):
                print("Upload terminated.")
                return
        self.users = valid
        self.list_manager.users = valid
        self.lottery = None
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._set_users(users, errors)

    def load_custom(self):
        path = input("Path to txt list: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            return
        self._set_users(users, errors)

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        for dept, cnt in info.items():
            print(f"  {dept}: {cnt}")

    def load_prizes(self):
        for e in self.prize_manager.load_default_prizes():
            print("  " + e)
        self.show_prizes()

    def add_prize(self):
        name = input("Prize name: ").strip()
        qty = input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = input("Avoidance groups (numbers or names, comma separated, empty for none): ").strip()
        avoid = []
        for tok in [t.strip() for t in raw.split(",") if t.strip()]:
            if tok.isdigit() and 1 <= int(tok) <= len(groups):
                avoid.append(groups[int(tok) - 1])
            else:
                avoid.append(tok)
        drawer = input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print("Prize added.")
        except ValueError as e:
            print(f"Error: {e}")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) if p.avoid_groups else "None"
            print(f"  {i}. {p.name} x{p.quantity} | avoid: {avoid} | drawer: {p.associated_drawer or 'None'}")

    def reorder(self):
        self.show_prizes()
        raw = input("New order (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Order updated.")
            self.show_prizes()
        else:
            print("Invalid order.")

    def run_lottery(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        lm = self.lottery
        for rnd, prize in enumerate(prizes, 1):
            if self.result_manager.get_winners_by_prize([prize])[prize.name]:
                print(f"Round {rnd} ({prize.name}) already drawn, skipped.")
                continue
            print(f"\n=== Round {rnd}: {prize.name} | Quantity: {prize.quantity} ===")
            print("Rules: " + lm.rule_description(prize))
            winners = []
            terminated = False
            for i in range(prize.quantity):
                print(f"Currently drawing the {ordinal(i + 1)} winner")
                while True:
                    cmd = input("[Enter]=draw, pause, terminate: ").strip().lower()
                    if cmd == "pause":
                        print("Lottery paused. Type 'continue' to resume or 'terminate' to end round.")
                        while True:
                            c2 = input("> ").strip().lower()
                            if c2 == "continue":
                                print("Resumed.")
                                break
                            if c2 == "terminate":
                                terminated = True
                                break
                        if terminated:
                            break
                        continue
                    if cmd == "terminate":
                        terminated = True
                    break
                if terminated:
                    print("Current round terminated.")
                    break
                user = lm.draw_one(prize)
                if user is None:
                    print("No eligible participants left.")
                    break
                winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lm.finish_round(prize, winners)
            print(f"--- Round {rnd} results ---")
            for i, u in enumerate(winners, 1):
                print(f"  {i}. {u.name} ({u.department}) - {prize.name}")
            if not winners:
                print("  (no winners)")
        self.show_summary()

    def show_summary(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Winner Summary =====")
        for pname, ws in grouped.items():
            print(f"[{pname}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {pname} @ {w.time:%H:%M:%S}")
            if not ws:
                print("  (none)")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prizes", self.load_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("View prizes", self.show_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.run_lottery),
            "9": ("Show summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        while True:
            print("\n==== Team Building Smart Lottery ====")
            for k, (label, _) in actions.items():
                print(f" {k}. {label}")
            print(" 0. Exit")
            try:
                choice = input("Choose: ").strip()
            except EOFError:
                break
            if choice == "0":
                break
            act = actions.get(choice)
            if act:
                try:
                    act[1]()
                except EOFError:
                    break
            else:
                print("Invalid choice.")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
