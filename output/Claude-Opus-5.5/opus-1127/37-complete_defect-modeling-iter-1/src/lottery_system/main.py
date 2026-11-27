"""Command-line interface of the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "0"


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    # ---------- list ----------
    def _accept_users(self, users, errors) -> None:
        if errors:
            print("Detected invalid data:")
            for e in errors:
                print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("Detected duplicate names:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        if errors or dups:
            choice = _input("Remove invalid data and continue (r) or terminate upload (t)? ").strip().lower()
            if choice != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        self.lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors)

    def load_custom(self) -> None:
        path = _input("Enter txt file path: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            return
        self._accept_users(users, errors)

    def view_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # ---------- prizes ----------
    def load_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")

    def add_prize(self) -> None:
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = _input("Avoid groups (numbers or names, comma separated, empty for none): ").strip()
        avoid = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                avoid.append(groups[int(token) - 1])
            else:
                avoid.append(token)
        drawer = _input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print("Prize added.")
        except ValueError as e:
            print(f"Error: {e}")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    def reorder(self) -> None:
        self.view_prizes()
        raw = _input("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        print("Order updated." if self.prize_manager.reorder_prizes(order) else "Invalid order.")

    # ---------- lottery ----------
    def start_lottery(self) -> None:
        if not self.lottery:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n===== Round {rnd}: {prize.name} (Quantity: {prize.quantity}) =====")
            print("Rules: " + self.lottery.describe_rules(prize))
            round_winners = []
            terminated = False
            for i in range(1, prize.quantity + 1):
                cmd = _input("Press Enter to draw, or type pause/terminate: ").strip().lower()
                while cmd == "pause":
                    print("Lottery paused.")
                    cmd = _input("Type 'continue' to resume or 'terminate' to skip round: ").strip().lower()
                    if cmd == "continue":
                        print("Lottery resumed.")
                        cmd = ""
                    elif cmd != "terminate":
                        cmd = "pause"
                if cmd == "terminate":
                    print("Current round terminated.")
                    terminated = True
                    break
                print(f"Currently drawing the {i}th winner...")
                w = self.lottery.draw_winner(prize)
                if w is None:
                    print("No eligible participants left for this prize.")
                    break
                self.result_manager.add_winner(w, prize)
                round_winners.append(w)
                print(f"Congratulations {w.name} ({w.department}) for winning {prize.name}")
            self.lottery.record_round_result(prize, round_winners)
            print(f"--- Round {rnd} results{' (terminated)' if terminated else ''} ---")
            for k, w in enumerate(round_winners, 1):
                print(f"  {k}. {w.name} ({w.department})")
        self.show_summary()

    def show_summary(self) -> None:
        print("\n===== Complete Winner List =====")
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        for prize_name, ws in grouped.items():
            for w in ws:
                print(f"  {w.user.name} | {w.user.department} | {prize_name}")
        if not self.result_manager.winners:
            print("  No winners yet.")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self) -> None:
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.view_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_summary,
            "10": self.export,
        }
        while True:
            print("\n==== Team Building Smart Lottery System ====")
            print("1. Load default list   2. Upload custom list   3. View groups")
            print("4. Load preset prizes  5. Add custom prize     6. View prizes")
            print("7. Reorder prizes      8. Start lottery        9. View winners")
            print("10. Export results     0. Exit")
            choice = _input("Select: ").strip()
            if choice == "0":
                print("Goodbye.")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice.")


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
