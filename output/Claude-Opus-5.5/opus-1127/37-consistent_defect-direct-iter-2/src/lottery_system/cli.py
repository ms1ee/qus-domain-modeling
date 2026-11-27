"""Command-line interface of the lottery system."""

import re
import sys

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class _Exit(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise _Exit()


class App:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.lottery = None
        self.results = ResultManager()
        self.drawn_prizes = []

    # ---------------------------------------------------------------- lists
    def _accept_users(self, users, errors) -> None:
        if errors:
            print("Detected invalid data:")
            for e in errors:
                print("  " + e)
            if not users:
                print("No valid data loaded.")
                return
            choice = ask("Remove invalid data and continue (r) or terminate upload (t)? [r/t]: ").lower()
            if choice != "r":
                print("Upload terminated.")
                return
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("Detected duplicate names:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
            choice = ask("Remove duplicates (keep first occurrence) (r) or terminate upload (t)? [r/t]: ").lower()
            if choice != "r":
                print("Upload terminated.")
                return
        self.users = valid
        print(f"List loaded: {len(valid)} valid participants.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors)

    def load_custom(self) -> None:
        path = ask("Enter txt list path (each line 'Name,Department Group'): ")
        users, errors = self.list_manager.load_custom_list(path)
        self._accept_users(users, errors)

    def show_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Valid groups:")
        for i, (dep, cnt) in enumerate(info.items(), 1):
            print(f"  {i}. {dep}: {cnt} people")

    # --------------------------------------------------------------- prizes
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Default prizes loaded.")

    def add_prize(self) -> None:
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            print("Groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (serial numbers or names, comma separated, empty for none): ")
        for token in re.split(r"[,;，；\s]+", raw) if raw else []:
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                g = groups[int(token) - 1]
            else:
                g = token
            if g not in avoid:
                avoid.append(g)
        drawer = ask("Associated lottery person (empty for none): ")
        try:
            prize = self.prize_manager.add_prize(name, qty, avoid, drawer or None)
            print(f"Prize added: {prize}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    def reorder(self) -> None:
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order as serial numbers (e.g. 3 1 2): ")
        try:
            order = [int(t) for t in re.split(r"[,;，；\s]+", raw) if t]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.show_prizes()
        else:
            print("Invalid order: must be a permutation of all serial numbers.")

    # -------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        self.lottery = LotteryManager(self.users)
        self.results = ResultManager()
        self.drawn_prizes = prizes
        print("Commands: Enter = draw next, 'pause' = pause, 'continue' = resume, "
              "'terminate' = end current round")
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print(self.lottery.describe_rules(prize))
            print("=" * 60)
            round_winners = []
            terminated = False
            for i in range(1, prize.quantity + 1):
                paused = False
                while True:
                    cmd = ask("(paused) > " if paused else f"[Draw #{i}] > ").lower()
                    if cmd == "terminate":
                        terminated = True
                        break
                    if cmd == "pause":
                        paused = True
                        print("Lottery paused. Enter 'continue' to resume.")
                        continue
                    if cmd == "continue":
                        if paused:
                            print("Lottery resumed.")
                        paused = False
                        continue
                    if paused:
                        print("Lottery is paused. Enter 'continue' or 'terminate'.")
                        continue
                    break
                if terminated:
                    print(f"Round '{prize.name}' terminated.")
                    break
                print(f"Currently drawing the {i}th winner...")
                user = self.lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                self.results.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.record_round(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if not round_winners:
                print("  No winners.")
            for n, u in enumerate(round_winners, 1):
                print(f"  {n}. {u.name} ({u.department})")
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        if not self.results.winners:
            print("No winners yet.")
            return
        print("\nComplete winner list:")
        for prize_name, winners in self.results.get_winners_by_prize(self.drawn_prizes).items():
            print(f"[{prize_name}]")
            if not winners:
                print("  (none)")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} - "
                      f"{w.win_time:%Y-%m-%d %H:%M:%S}")

    def export(self) -> None:
        ok, msg = self.results.export_to_csv(self.drawn_prizes)
        print(msg)

    # ----------------------------------------------------------------- menu
    def run(self) -> None:
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.show_groups),
            "4": ("Load default prizes", self.load_default_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("View prizes", self.show_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.run_lottery),
            "9": ("Show winner summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        print("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                print()
                for k, (label, _) in actions.items():
                    print(f"{k}. {label}")
                print("0. Exit")
                choice = ask("Select: ")
                if choice == "0":
                    break
                action = actions.get(choice)
                if action:
                    action[1]()
                else:
                    print("Invalid choice.")
        except (_Exit, KeyboardInterrupt):
            print()
        print("Goodbye.")


def main() -> int:
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
