"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import List

from lottery_system.models import User
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


class LotteryCLI:
    def __init__(self) -> None:
        self.status = "idle"
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager = None

    def _input(self, prompt: str) -> str:
        try:
            return input(prompt).strip()
        except EOFError:
            return "0"

    # ----- list -----
    def _set_users(self, users):
        self.users = users
        self.result_manager = ResultManager()
        self.lottery_manager = None
        print(f"{len(users)} valid participants loaded.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, _ = self.list_manager.validate_users(users)
        for e in errors:
            print(e)
        self._set_users(valid)

    def load_custom(self):
        path = self._input("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            print("Validation issues found:")
            for e in errors:
                print("  " + e)
            for d in duplicates:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            if not valid:
                print("No valid data. Upload terminated.")
                return
            choice = self._input("Enter 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
            if choice != "r":
                print("Upload terminated.")
                return
            print("Invalid data removed.")
        if not valid:
            print("No valid data loaded.")
            return
        self._set_users(valid)

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Department groups:")
        for dept, cnt in info.items():
            print(f"  {dept}: {cnt} people")

    # ----- prizes -----
    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    def add_prize(self):
        name = self._input("Prize name: ")
        qty = self._input("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = self._input("Avoidance groups (numbers or names, comma separated, blank for none): ")
        avoid = []
        for tok in raw.replace("，", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.isdigit() and 1 <= int(tok) <= len(groups):
                avoid.append(groups[int(tok) - 1])
            else:
                avoid.append(tok)
        drawer = self._input("Associated lottery person (blank for none): ") or None
        if self.prize_manager.add_prize(name, qty, avoid, drawer):
            print("Prize added.")
        else:
            print("Invalid prize (name must be non-empty and quantity a positive integer).")

    def reorder(self):
        self.view_prizes()
        raw = self._input("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        print("Order updated." if self.prize_manager.reorder_prizes(order) else "Invalid order.")

    # ----- lottery -----
    def _control(self) -> str:
        """Return 'draw' or 'terminate'."""
        while True:
            cmd = self._input("[Enter]=draw, 'pause', 'terminate': ").lower()
            if cmd in ("", "draw", "continue"):
                return "draw"
            if cmd == "terminate":
                return "terminate"
            if cmd == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
                while True:
                    c = self._input("> ").lower()
                    if c == "continue":
                        print("Resumed.")
                        return "draw"
                    if c == "terminate":
                        return "terminate"
                    print("Paused. Type 'continue' or 'terminate'.")
            print("Unknown command.")

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
        lm = self.lottery_manager
        self.status = "running"
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 50)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            if prize.associated_drawer:
                print(f"Lottery person: {prize.associated_drawer}")
            print(f"Rule: {lm.describe_rule(prize)}")
            round_winners = []
            for i in range(1, prize.quantity + 1):
                if self._control() == "terminate":
                    print("Current round terminated.")
                    break
                print(f"Currently drawing the {ordinal(i)} winner...")
                user = lm.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lm.finish_round(prize, round_winners)
            print(f"Round {rnd} results:")
            if not round_winners:
                print("  (no winners)")
            for j, u in enumerate(round_winners, 1):
                print(f"  {j}. {u.name} ({u.department}) - {prize.name}")
        self.status = "finished"
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for pname, winners in data.items():
            if not winners:
                continue
            print(f"[{pname}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {pname} - "
                      f"{w.win_time.strftime('%H:%M:%S')}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": lambda: [print(e) for e in self.prize_manager.load_default_prizes()] and None,
            "5": self.add_prize, "6": self.view_prizes, "7": self.reorder,
            "8": self.start_lottery, "9": self.show_summary, "10": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery =====")
            print("1. Load default list      2. Upload custom list    3. View groups")
            print("4. Load preset prizes     5. Add custom prize      6. View prizes")
            print("7. Reorder prizes         8. Start lottery         9. View results")
            print("10. Export results        0. Exit")
            choice = self._input("Choose: ")
            if choice == "0":
                print("Bye.")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice.")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
