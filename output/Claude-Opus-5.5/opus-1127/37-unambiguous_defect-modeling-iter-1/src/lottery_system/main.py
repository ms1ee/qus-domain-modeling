"""Command line interface of the lottery system."""

from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "q"


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []

    # ---------- list ----------
    def load_list(self):
        mode = _input("1) Default list  2) Custom txt list (name,department per line): ").strip()
        if mode == "2":
            path = _input("Path to txt file: ").strip()
            users, errors = self.list_manager.load_custom_list(path)
        else:
            users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = _input("Remove invalid data and continue (r) or terminate upload (t)? ").strip().lower()
            if choice != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} valid participants.")

    def show_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
        for g, c in info.items():
            print(f"  {g}: {c}")

    # ---------- prizes ----------
    def add_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = _input("Avoidance groups (comma separated, blank for none): ").strip()
        drawer = _input("Associated lottery person (blank for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, [g for g in groups.split(",") if g.strip()], drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def reorder(self):
        self.show_prizes()
        raw = _input("New order (e.g. 3 1 2): ").replace(",", " ").split()
        print("Reordered." if self.prize_manager.reorder_prizes(raw) else "Invalid order.")

    # ---------- lottery ----------
    def run_lottery(self):
        prizes = self.prize_manager.get_prizes()
        if not self.users or not prizes:
            print("Please load a list and configure prizes first.")
            return
        manager = LotteryManager(self.users)
        for w in self.result_manager.winners:
            manager.mark_winner(w.user)
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n=== Round {rnd}: {prize.name} | Quantity: {prize.quantity} ===")
            print(f"Rule: {manager.get_rule_description(prize)}")
            round_winners = []
            i = 0
            while i < prize.quantity:
                cmd = _input(f"[Enter]=draw #{i + 1}, 'pause', 'terminate': ").strip().lower()
                if cmd == "q":
                    cmd = "terminate"
                if cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume.")
                    while True:
                        c = _input("> ").strip().lower()
                        if c == "continue":
                            print("Resumed.")
                            break
                        if c in ("terminate", "q"):
                            cmd = "terminate"
                            break
                    if cmd != "terminate":
                        continue
                if cmd == "terminate":
                    print("Round terminated.")
                    break
                print(f"Currently drawing the {i + 1}th winner...")
                user = manager.draw_one(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
                i += 1
            manager.finish_round(prize, round_winners)
            print(f"--- Round {rnd} results ---")
            for n, u in enumerate(round_winners, 1):
                print(f"  {n}. {u.name} ({u.department})")
        self.show_summary()

    def show_summary(self):
        print("\n=== Complete Winner List ===")
        for pname, ws in self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes()).items():
            print(f"{pname}:")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {pname}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_list, "2": self.show_groups,
            "3": lambda: print("\n".join(self.prize_manager.load_default_prizes()) or "Preset prizes loaded."),
            "4": self.add_prize, "5": self.show_prizes, "6": self.reorder,
            "7": self.run_lottery, "8": self.show_summary, "9": self.export,
        }
        while True:
            print("\n1) Load list 2) View groups 3) Load preset prizes 4) Add prize 5) View prizes "
                  "6) Reorder prizes 7) Start lottery 8) Show results 9) Export 0) Exit")
            c = _input("Choice: ").strip()
            if c in ("0", "q"):
                break
            action = actions.get(c)
            if action:
                action()
            else:
                print("Invalid choice.")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
