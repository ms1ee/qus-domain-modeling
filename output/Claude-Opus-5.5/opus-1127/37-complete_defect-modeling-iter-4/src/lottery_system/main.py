"""Command-line interface for the lottery system."""

from __future__ import annotations

import sys

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class ExitProgram(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise ExitProgram()


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryApp:
    def __init__(self):
        self.status = "idle"
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    # ---------------- list --------------------
    def set_users(self, users):
        self.users = users
        self.lottery = None
        self.result_manager = ResultManager()
        print(f"{len(users)} valid participants loaded.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        for e in errors:
            print("  " + e)
        self.set_users(valid)

    def load_custom(self):
        path = ask("Enter path of txt list file: ")
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("Upload failed.")
            return
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Validation issues detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            while True:
                c = ask("Remove invalid data and continue (r) or terminate upload (t)? ").lower()
                if c == "r":
                    break
                if c == "t":
                    print("Upload terminated.")
                    return
        self.set_users(valid)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for g, c in info.items():
            print(f"  {g}: {c} people")

    # ---------------- prizes --------------------
    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def load_presets(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def choose_groups(self):
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if not groups:
            text = ask("Enter avoidance groups (comma separated, empty for none): ")
            return [g.strip() for g in text.replace("\uff0c", ",").split(",") if g.strip()]
        for i, g in enumerate(groups, 1):
            print(f"  {i}. {g}")
        text = ask("Select avoidance groups by number (comma separated, empty for none): ")
        result = []
        for part in text.replace("\uff0c", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                result.append(groups[int(part) - 1])
            else:
                print(f"  Ignored invalid selection: {part}")
        return result

    def add_prize(self):
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        drawer = ask("Associated lottery person (empty for none): ") or None
        groups = self.choose_groups()
        try:
            self.prize_manager.add_prize(name, qty, groups, drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_avoidance(self):
        self.view_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        idx = ask("Select prize number: ")
        if not idx.isdigit() or not (1 <= int(idx) <= len(prizes)):
            print("Invalid selection.")
            return
        groups = self.choose_groups()
        self.prize_manager.set_avoid_groups(int(idx) - 1, groups)
        print("Avoidance groups updated.")

    def reorder(self):
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        text = ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        parts = [x.strip() for x in text.replace("\uff0c", ",").replace(" ", ",").split(",") if x.strip()]
        if self.prize_manager.reorder_prizes(parts):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order.")

    # ---------------- lottery --------------------
    def start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        for w in self.result_manager.winners:
            self.lottery.mark_winner(w.user)
        self.status = "running"
        for rnd, prize in enumerate(prizes, 1):
            remaining = prize.quantity - self.result_manager.count_for_prize(prize)
            if remaining <= 0:
                continue
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity} (remaining {remaining})")
            print(f"Rules: {prize.rule_description()}")
            if self.lottery.is_fallback_active(prize):
                print("Fallback active: prize pool limited to Cheng Ru group members.")
            round_winners = []
            terminated = False
            for i in range(remaining):
                while True:
                    cmd = ask("[Enter]=draw | pause | terminate: ").lower()
                    if cmd == "pause":
                        print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                        while True:
                            c = ask("> ").lower()
                            if c in ("continue", "terminate"):
                                break
                        cmd = c
                    if cmd == "terminate":
                        terminated = True
                        break
                    if cmd in ("", "continue", "draw"):
                        break
                    print("Unknown command.")
                if terminated:
                    print("Current round terminated.")
                    break
                print(f"Currently drawing the {ordinal(i + 1)} winner...")
                user = self.lottery.draw_winner(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.record_round_result(prize, round_winners)
            print(f"-- Round {rnd} results --")
            if round_winners:
                for n, u in enumerate(round_winners, 1):
                    print(f"  {n}. {u.name} ({u.department})")
            else:
                print("  No winners this round.")
        self.status = "finished"
        print("\nAll rounds completed.")
        self.show_all()

    def show_all(self):
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("Complete winner list:")
        any_w = False
        for pname, ws in grouped.items():
            for w in ws:
                any_w = True
                print(f"  {w.user.name}, {w.user.department}, {pname}")
        if not any_w:
            print("  (none)")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prize library", self.load_presets),
            "5": ("Add custom prize", self.add_prize),
            "6": ("Configure avoidance groups", self.configure_avoidance),
            "7": ("Reorder prizes", self.reorder),
            "8": ("View prizes", self.view_prizes),
            "9": ("Start lottery", self.start_lottery),
            "10": ("View all winners", self.show_all),
            "11": ("Export results", self.export),
        }
        try:
            while True:
                print("\n===== Team Building Smart Lottery System =====")
                for k, (label, _) in actions.items():
                    print(f"{k}. {label}")
                print("0. Exit")
                c = ask("Choose: ")
                if c == "0":
                    break
                if c in actions:
                    actions[c][1]()
                else:
                    print("Invalid option.")
        except (ExitProgram, KeyboardInterrupt):
            pass
        print("Goodbye.")


def main():
    LotteryApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
