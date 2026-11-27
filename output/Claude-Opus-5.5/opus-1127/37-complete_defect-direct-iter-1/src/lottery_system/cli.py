"""Command-line interface."""

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


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_done = False

    # ---------- list ----------
    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors)

    def load_custom(self):
        path = _input("Enter txt list path: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("Upload failed.")
            return
        self._accept_users(users, errors)

    def _accept_users(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Invalid data detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = _input("Type 'r' to remove invalid data and continue, "
                            "'t' to terminate upload: ").strip().lower()
            if choice != "r":
                print("Upload terminated.")
                return
        self.users = valid
        print(f"Loaded {len(valid)} valid participants.")

    def view_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Current valid groups:")
        for g, c in info.items():
            print(f"  {g}: {c} people")

    # ---------- prizes ----------
    def _choose_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            raw = _input("Select avoidance groups by number (comma separated) "
                         "or type names, blank for none: ").strip()
        else:
            raw = _input("Enter avoidance group names (comma separated), "
                         "blank for none: ").strip()
        result = []
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                g = groups[int(part) - 1]
            else:
                g = part
            if g not in result:
                result.append(g)
        return result

    def add_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = self._choose_groups()
        drawer = _input("Associated lottery person (blank for none): ").strip()
        try:
            self.prize_manager.add_prize(name, qty, groups, drawer or None)
            print("Prize added.")
        except ValueError as e:
            print(f"Error: {e}")

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")

    def set_avoid_groups(self):
        prizes = self.prize_manager.get_prizes()
        if not self.list_prizes():
            return
        raw = _input("Select prize number: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            print("Invalid selection.")
            return
        prizes[int(raw) - 1].avoid_groups = self._choose_groups()
        print("Avoidance groups updated.")

    def list_prizes(self) -> bool:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return False
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | drawer: "
                  f"{p.associated_drawer or '-'} | avoid: "
                  f"{', '.join(p.avoid_groups) or '-'}")
        return True

    def reorder(self):
        if not self.list_prizes():
            return
        raw = _input("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Order updated.")
            self.list_prizes()
        else:
            print("Invalid order.")

    # ---------- lottery ----------
    def run_lottery(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        self.result_manager = ResultManager()
        engine = LotteryManager(self.users)
        print("Commands during lottery: Enter = draw next, 'pause', "
              "'continue', 'terminate' (end current round).")
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n=== Round {rnd}: {prize.name} | Quantity: {prize.quantity}"
                  f" | Drawer: {prize.associated_drawer or '-'} ===")
            print(f"Rules: {prize.rule_description()}")
            if engine.is_fallback_active(prize):
                print("Fallback activated: prize pool limited to Cheng Ru group.")
            round_winners = []
            paused = False
            terminated = False
            i = 0
            while i < prize.quantity:
                cmd = _input("[paused] > " if paused else
                             f"(draw {i + 1}/{prize.quantity}) > ").strip().lower()
                if cmd == "terminate":
                    print("Current round terminated.")
                    terminated = True
                    break
                if cmd == "pause":
                    paused = True
                    print("Lottery paused. Type 'continue' to resume.")
                    continue
                if cmd == "continue":
                    if paused:
                        print("Lottery resumed.")
                    paused = False
                    continue
                if paused:
                    print("Lottery is paused. Type 'continue' or 'terminate'.")
                    continue
                print(f"Currently drawing the {i + 1}th winner...")
                user = engine.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) "
                      f"for winning {prize.name}")
                i += 1
            engine.finish_round(prize, round_winners)
            print(f"--- Round {rnd} results ({prize.name}) ---")
            if round_winners:
                for n, u in enumerate(round_winners, 1):
                    print(f"  {n}. {u.name} ({u.department})")
            else:
                print("  No winners.")
            if terminated:
                continue
        self.lottery_done = True
        self.show_summary()

    def show_summary(self):
        grouped = self.result_manager.get_winners_by_prize(
            self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        any_w = False
        for pname, ws in grouped.items():
            for w in ws:
                any_w = True
                print(f"  {w.user.name}, {w.user.department}, {pname}")
        if not any_w:
            print("  No winners yet.")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------- main loop ----------
    def run(self):
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.view_groups),
            "4": ("Load preset prizes", self.load_default_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("Set prize avoidance groups", self.set_avoid_groups),
            "7": ("View prizes", self.list_prizes),
            "8": ("Reorder prizes", self.reorder),
            "9": ("Start lottery", self.run_lottery),
            "10": ("View winner list", self.show_summary),
            "11": ("Export results", self.export),
        }
        while True:
            print("\n==== Team Building Smart Lottery ====")
            for k, (label, _) in actions.items():
                print(f" {k}. {label}")
            print(" 0. Exit")
            choice = _input("Select: ").strip()
            if choice in ("0", "terminate", "exit", "quit"):
                print("Bye.")
                return
            action = actions.get(choice)
            if action:
                action[1]()
            else:
                print("Invalid option.")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
