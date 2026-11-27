"""Command-line interface for the lottery system."""

import sys

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class ExitApp(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        raise ExitApp()


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class App:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery_manager = None

    # ---------------------------------------------------------------- list
    def menu_load_list(self):
        print("\n1. Load built-in default list\n2. Upload custom txt list")
        choice = ask("Choose: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = ask("Enter txt file path: ").strip()
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid choice.")
            return
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            print("\nProblems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in duplicates:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            if not valid:
                print("No valid data. Upload terminated.")
                return
            ans = ask("Type 'r' to remove invalid data and continue, 't' to terminate upload: ")
            if ans.strip().lower() != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid data loaded.")
            return
        self.users = valid
        self.lottery_manager = None
        print(f"Loaded {len(valid)} valid participants.")

    def menu_view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nCurrent valid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")
        print(f"Total: {len(self.users)} people")

    # --------------------------------------------------------------- prize
    def _groups(self):
        return list(self.list_manager.get_group_info(self.users).keys())

    def _select_groups(self):
        groups = self._groups()
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names, comma-separated, empty for none): ").strip()
        if not raw:
            return []
        selected = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                g = groups[int(token) - 1]
            else:
                g = token
            if g not in selected:
                selected.append(g)
        return selected

    def _show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return False
        print("\nPrize order:")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")
        return True

    def menu_prizes(self):
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Reorder prizes")
            print("5. View prizes")
            print("0. Back")
            c = ask("Choose: ").strip()
            if c == "1":
                errors = self.prize_manager.load_default_prizes()
                for e in errors:
                    print("  " + e)
                print("Preset prizes loaded.")
            elif c == "2":
                name = ask("Prize name: ").strip()
                qty = ask("Quantity: ").strip()
                avoid = self._select_groups()
                drawer = ask("Associated lottery person (empty for none): ").strip() or None
                try:
                    p = self.prize_manager.add_prize(name, qty, avoid, drawer)
                    print(f"Added: {p}")
                except ValueError as exc:
                    print(f"Error: {exc}")
            elif c == "3":
                if not self._show_prizes():
                    continue
                idx = ask("Prize number: ").strip()
                if not idx.isdigit():
                    print("Invalid number.")
                    continue
                groups = self._select_groups()
                if self.prize_manager.set_avoid_groups(int(idx) - 1, groups):
                    print("Avoidance groups updated.")
                else:
                    print("Invalid prize number.")
            elif c == "4":
                if not self._show_prizes():
                    continue
                raw = ask("Enter new order of serial numbers (e.g. 3,1,2): ").strip()
                try:
                    order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
                except ValueError:
                    order = []
                if self.prize_manager.reorder_prizes(order):
                    print("Prizes reordered.")
                    self._show_prizes()
                else:
                    print("Invalid order.")
            elif c == "5":
                self._show_prizes()
            elif c == "0":
                return
            else:
                print("Invalid choice.")

    # ------------------------------------------------------------- lottery
    def run_round(self, prize):
        lm = self.lottery_manager
        print("\n" + "=" * 60)
        print(f"Prize: {prize.name} | Quantity: {prize.quantity}")
        print(f"Rules: {lm.describe_rules(prize)}")
        print("=" * 60)
        round_winners = []
        paused = False
        while len(round_winners) < prize.quantity:
            idx = len(round_winners) + 1
            if paused:
                cmd = ask("[Paused] Type 'continue' to resume or 'terminate' to end this round: ")
            else:
                print(f"Currently drawing the {ordinal(idx)} winner")
                cmd = ask("Press Enter to draw (commands: pause / terminate): ")
            cmd = cmd.strip().lower()
            if cmd == "terminate":
                print("Current round terminated and skipped.")
                break
            if cmd == "pause":
                paused = True
                print("Lottery paused.")
                continue
            if cmd == "continue":
                if paused:
                    paused = False
                    print("Lottery resumed.")
                continue
            if paused:
                print("Lottery is paused.")
                continue
            if cmd not in ("", "draw", "d"):
                print("Unknown command.")
                continue
            user = lm.draw_one(prize)
            if user is None:
                print("No eligible participants left for this prize.")
                break
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        lm.finish_round(prize, round_winners)
        print(f"\nResults of round '{prize.name}':")
        if not round_winners:
            print("  (no winners)")
        for i, u in enumerate(round_winners, 1):
            print(f"  {i}. {u.name} ({u.department})")

    def menu_start(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.result_manager.winners:
            ans = ask("Previous results exist. Reset them? (y/n): ").strip().lower()
            if ans == "y":
                self.result_manager.clear()
                self.lottery_manager = None
        if self.lottery_manager is None:
            self.lottery_manager = LotteryManager(self.users, self.result_manager)
        for prize in prizes:
            self.run_round(prize)
        print("\nAll rounds completed.")
        self.menu_summary()

    def menu_summary(self):
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        for prize_name, ws in grouped.items():
            print(f"[{prize_name}]")
            if not ws:
                print("  (no winners)")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - "
                      f"{w.win_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def menu_export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------------------------------------------------------------- main
    def run(self):
        print("Welcome to the Team Building Smart Lottery System")
        while True:
            print("\n===== Main Menu =====")
            print("1. Load list")
            print("2. View groups")
            print("3. Prize configuration")
            print("4. Start lottery")
            print("5. View results summary")
            print("6. Export results")
            print("0. Exit")
            c = ask("Choose: ").strip()
            actions = {
                "1": self.menu_load_list,
                "2": self.menu_view_groups,
                "3": self.menu_prizes,
                "4": self.menu_start,
                "5": self.menu_summary,
                "6": self.menu_export,
            }
            if c == "0":
                print("Goodbye!")
                return
            action = actions.get(c)
            if action:
                action()
            else:
                print("Invalid choice.")


def main():
    try:
        App().run()
    except (ExitApp, KeyboardInterrupt):
        print("\nExiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
