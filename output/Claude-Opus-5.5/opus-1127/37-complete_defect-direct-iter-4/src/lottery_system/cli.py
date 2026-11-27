"""Command-line interface for the lottery system."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "terminate"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryApp:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_done = False

    # ---------------- list ---------------- #
    def _accept_list(self, users, errors) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            print("\nList verification found problems:")
            for e in errors:
                print("  " + e)
            for d in duplicates:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = _input("Enter 'r' to remove invalid data and continue, "
                            "'t' to terminate upload: ").strip().lower()
            if choice != "r":
                print("Upload terminated. List unchanged.")
                return
        if not valid:
            print("No valid users loaded.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} valid users.")

    def load_default(self) -> None:
        self._accept_list(*self.list_manager.load_default_list())

    def load_custom(self) -> None:
        path = _input("Enter txt file path: ").strip().strip('"')
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("Upload failed.")
            return
        self._accept_list(users, errors)

    def view_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # ---------------- prizes ---------------- #
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Default prizes loaded.")

    def add_custom_prize(self) -> None:
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid: List[str] = []
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = _input("Avoid groups (numbers or names separated by commas, blank for none): ").strip()
        for item in raw.replace("\uff0c", ",").split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit() and 1 <= int(item) <= len(groups):
                g = groups[int(item) - 1]
            else:
                g = item
            if g not in avoid:
                avoid.append(g)
        drawer = _input("Associated lottery person (blank for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Added prize: {p}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nCurrent prize order:")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    def reorder(self) -> None:
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = _input("Enter new order as serial numbers (e.g. 3,1,2), blank to keep: ").strip()
        if not raw:
            return
        try:
            order = [int(x) for x in raw.replace("\uff0c", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.show_prizes()
        else:
            print("Invalid order. Must be a permutation of current serial numbers.")

    # ---------------- lottery ---------------- #
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        self.result_manager = ResultManager()
        engine = LotteryManager(self.users)
        print("\nCommands during draw: Enter = draw next, 'pause', 'continue', 'terminate'")
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print(f"Rules: {engine.describe_rules(prize)}")
            print("=" * 60)
            pool = engine._get_eligible_pool(prize)
            round_winners: List[User] = []
            terminated = False
            for i in range(1, prize.quantity + 1):
                cmd = _input(f"[{_ordinal(i)} winner] Press Enter to draw: ").strip().lower()
                while cmd == "pause":
                    print("Lottery paused.")
                    cmd = _input("Type 'continue' to resume or 'terminate' to skip round: ").strip().lower()
                    if cmd == "continue":
                        print("Lottery resumed.")
                        break
                    if cmd != "terminate":
                        cmd = "pause"
                if cmd == "terminate":
                    print("Current round terminated and skipped.")
                    terminated = True
                    break
                print(f"Currently drawing the {_ordinal(i)} winner...")
                user = engine.draw_one(prize, pool)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                round_winners.append(user)
                self.result_manager.add_winner(user, prize)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            engine.record_round_result(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if round_winners:
                for k, u in enumerate(round_winners, 1):
                    print(f"  {k}. {u.name} ({u.department})")
            else:
                print("  No winners.")
            if terminated:
                continue
        self.lottery_done = True
        self.show_summary()

    def show_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        data = self.result_manager.get_winners_by_prize(prizes)
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        print("\n========== Complete Winner List ==========")
        for pname, winners in data.items():
            print(f"{pname}:")
            if not winners:
                print("  (none)")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {pname}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------------- main loop ---------------- #
    def run(self) -> None:
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_default_prizes, "5": self.add_custom_prize,
            "6": self.show_prizes, "7": self.reorder, "8": self.run_lottery,
            "9": self.show_summary, "10": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            print(" 1. Load default list        2. Upload custom txt list")
            print(" 3. View groups              4. Load preset prizes")
            print(" 5. Add custom prize         6. View prizes")
            print(" 7. Reorder prizes           8. Start lottery")
            print(" 9. View all winners        10. Export results")
            print(" 0. Exit")
            choice = _input("Select: ").strip()
            if choice in ("0", "terminate", "exit", "quit"):
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid option.")


def main() -> None:
    LotteryApp().run()


if __name__ == "__main__":
    main()
