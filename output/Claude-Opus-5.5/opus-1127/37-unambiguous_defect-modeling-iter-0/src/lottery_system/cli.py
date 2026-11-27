"""Command-line interface for the lottery system."""

from __future__ import annotations

import sys
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
        raise SystemExit(0)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotterySystem:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager = LotteryManager([])
        self.drawn_prizes = set()
        self.list_loading_mode = ""

    # ------------------------------------------------------------------ lists
    def _accept_users(self, users, errors, mode) -> None:
        for e in errors:
            print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        for d in dups:
            print(f"  Duplicate Name: {d.name} ({d.department})")
        if errors or dups:
            choice = _input("Invalid data detected. [r] remove invalid data and continue, "
                            "[t] terminate upload: ").strip().lower()
            if choice != "r":
                print("Upload terminated. Current list unchanged.")
                return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        self.list_loading_mode = mode
        self.lottery_manager = LotteryManager(valid)
        self.result_manager.clear()
        self.drawn_prizes.clear()
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors, "default")

    def load_custom(self):
        path = _input("Enter txt file path (format per line: Name,Department): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users:
            for e in errors:
                print("  " + e)
            print("No participants loaded.")
            return
        self._accept_users(users, errors, "custom")

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for i, (dep, cnt) in enumerate(info.items(), 1):
            print(f"  {i}. {dep}: {cnt} people")

    # ----------------------------------------------------------------- prizes
    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def add_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups: " + ", ".join(f"{i}.{g}" for i, g in enumerate(groups, 1)))
        raw = _input("Avoidance groups (numbers or names, comma-separated, empty for none): ").strip()
        avoid = []
        for tok in [t.strip() for t in raw.replace("\uff0c", ",").split(",") if t.strip()]:
            if tok.isdigit() and 1 <= int(tok) <= len(groups):
                avoid.append(groups[int(tok) - 1])
            else:
                avoid.append(tok)
        drawer = _input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            status = " [drawn]" if p.name in self.drawn_prizes else ""
            print(f"  {i}. {p.name} x{p.quantity} | avoid: {', '.join(p.avoid_groups) or 'none'}"
                  f" | lottery person: {p.associated_drawer or 'none'}{status}")

    def reorder(self):
        self.view_prizes()
        raw = _input("Enter new order as serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order. Must be a permutation of all serial numbers.")

    # ---------------------------------------------------------------- lottery
    def run_round(self, round_no, prize):
        lm = self.lottery_manager
        print("\n" + "=" * 60)
        print(f"Round {round_no}: {prize.name} | Quantity: {prize.quantity}")
        print(f"Rules: {lm.describe_rules(prize)}")
        print("Commands: [Enter] draw next, 'pause', 'continue', 'terminate'")
        round_winners = []
        paused = False
        terminated = False
        for i in range(prize.quantity):
            while True:
                cmd = _input("(paused) > " if paused else "> ").strip().lower()
                if cmd == "terminate":
                    terminated = True
                    break
                if paused:
                    if cmd == "continue":
                        paused = False
                        print("Lottery resumed.")
                        continue
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to end round.")
                    continue
                if cmd == "pause":
                    paused = True
                    print("Lottery paused.")
                    continue
                if cmd in ("", "continue", "draw"):
                    break
                print("Unknown command.")
            if terminated:
                print("Current round terminated.")
                break
            print(f"Currently drawing the {ordinal(i + 1)} winner...")
            user = lm.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize.")
                break
            self.result_manager.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        lm.record_round_result(prize, round_winners)
        self.drawn_prizes.add(prize.name)
        print(f"--- Round {round_no} results ({prize.name}) ---")
        if not round_winners:
            print("  No winners.")
        for i, u in enumerate(round_winners, 1):
            print(f"  {i}. {u.name} ({u.department})")

    def start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = [p for p in self.prize_manager.get_prizes() if p.name not in self.drawn_prizes]
        if not prizes:
            print("No pending prizes to draw.")
            return
        all_prizes = self.prize_manager.get_prizes()
        for p in prizes:
            self.run_round(all_prizes.index(p) + 1, p)
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for prize_name, ws in data.items():
            if not ws:
                continue
            print(f"[{prize_name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} "
                      f"@ {w.win_time:%H:%M:%S}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ------------------------------------------------------------------- menu
    def run(self):
        actions = {
            "1": ("Load default team building list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prize library", self.load_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("View prizes", self.view_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.start_lottery),
            "9": ("View winner summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            for k, (label, _) in actions.items():
                print(f" {k}. {label}")
            print(" 0. Exit")
            choice = _input("Select: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action[1]()
            else:
                print("Invalid choice.")


def main():
    try:
        LotterySystem().run()
    except KeyboardInterrupt:
        print("\nExited.")
        sys.exit(0)


if __name__ == "__main__":
    main()
