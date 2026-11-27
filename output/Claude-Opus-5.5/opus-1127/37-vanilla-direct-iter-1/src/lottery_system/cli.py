"""Command-line interface for the lottery system."""

import time

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class _Exit(Exception):
    pass


def _input(prompt):
    try:
        return input(prompt)
    except EOFError:
        raise _Exit()


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None

    # ------------------------------------------------------------ list
    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        for e in errors:
            print("  " + e)
        for d in dups:
            print(f"  Duplicate name removed: {d.name} ({d.department})")
        self.users = valid
        self.lottery = None
        print(f"Default list loaded: {len(valid)} participants.")

    def load_custom(self):
        path = _input("Enter path of txt list file: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if errors and not users:
            for e in errors:
                print("  " + e)
            print("No valid data loaded.")
            return
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Problems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate name: {d.name} ({d.department})")
            while True:
                c = _input("Input 'r' to remove invalid data and continue, "
                           "'t' to terminate upload: ").strip().lower()
                if c == "t":
                    print("Upload terminated.")
                    return
                if c == "r":
                    break
        if not valid:
            print("No valid participants in the list.")
            return
        self.users = valid
        self.lottery = None
        print(f"Custom list loaded: {len(valid)} participants.")

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for dept, cnt in info.items():
            print(f"  {dept}: {cnt} people")

    # ----------------------------------------------------------- prizes
    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) if p.avoid_groups else "none"
            print(f"  {i}. {p.name} x{p.quantity} | drawer: "
                  f"{p.associated_drawer or 'N/A'} | avoid: {avoid}")

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def _select_groups(self):
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = _input("Enter avoidance groups (numbers or names, comma separated, "
                     "empty for none): ").strip()
        result = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                token = groups[int(token) - 1]
            if token not in result:
                result.append(token)
        return result

    def add_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        drawer = _input("Associated lottery person (empty for none): ").strip() or None
        groups = self._select_groups()
        try:
            self.prize_manager.add_prize(name, qty, groups, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def set_avoid(self):
        self.view_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        raw = _input("Prize number: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            print("Invalid prize number.")
            return
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(int(raw) - 1, groups)
        print("Avoidance groups updated.")

    def reorder(self):
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = _input("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order: must be a permutation of all serial numbers.")

    # ---------------------------------------------------------- lottery
    def start_lottery(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print("Rule: " + self.lottery.describe_rule(prize))
            print("Commands: [Enter]=draw, pause, continue, terminate")
            round_winners = []
            paused = False
            terminated = False
            while len(round_winners) < prize.quantity:
                cmd = _input("> ").strip().lower()
                if cmd == "pause":
                    paused = True
                    print("Lottery paused. Input 'continue' to resume.")
                    continue
                if cmd == "continue":
                    if paused:
                        print("Lottery resumed.")
                    paused = False
                    continue
                if cmd == "terminate":
                    terminated = True
                    print("Current round terminated.")
                    break
                if paused:
                    print("Lottery is paused. Input 'continue' to resume "
                          "or 'terminate' to skip this round.")
                    continue
                n = len(round_winners) + 1
                print(f"Currently drawing the {n}th winner...")
                time.sleep(0.2)
                user = self.lottery.draw_one(prize)
                if user is None:
                    print("No eligible candidates remain for this prize.")
                    break
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) "
                      f"for winning {prize.name}")
            self.lottery.complete_round(prize, round_winners)
            print(f"--- Round {rnd} results ({prize.name}) ---")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            else:
                print("  No winners.")
            if terminated:
                continue
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not any(data.values()):
            print("No winners yet.")
            return
        for name, ws in data.items():
            print(f"[{name}]")
            if not ws:
                print("  (none)")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {name} - "
                      f"{w.time.strftime('%H:%M:%S')}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # -------------------------------------------------------------- run
    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_default_prizes, "5": self.add_prize, "6": self.set_avoid,
            "7": self.reorder, "8": self.view_prizes, "9": self.start_lottery,
            "10": self.show_summary, "11": self.export,
        }
        menu = """
====== Team Building Smart Lottery System ======
 1. Load default list          2. Upload custom txt list
 3. View groups                4. Load preset prizes
 5. Add custom prize           6. Set prize avoidance groups
 7. Reorder prizes             8. View prizes
 9. Start lottery             10. View result summary
11. Export results             0. Exit"""
        try:
            while True:
                print(menu)
                choice = _input("Select: ").strip()
                if choice == "0":
                    break
                action = actions.get(choice)
                if action:
                    action()
                else:
                    print("Invalid choice.")
        except (_Exit, KeyboardInterrupt):
            print()
        print("Goodbye!")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
