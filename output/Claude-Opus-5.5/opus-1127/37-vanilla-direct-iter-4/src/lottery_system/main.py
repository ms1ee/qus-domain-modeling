"""Command-line interface for the lottery system."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class App:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery = None

    # ----------------------------------------------------------------- lists
    def _accept_list(self, users, errors) -> None:
        for e in errors:
            print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        for d in dups:
            print(f"  Duplicate name detected: {d.name} ({d.department})")
        if errors or dups:
            while True:
                c = input("Invalid data found. 'r' remove invalid data and continue / "
                          "'t' terminate upload: ").strip().lower()
                if c == "r":
                    break
                if c == "t":
                    print("Upload terminated. List unchanged.")
                    return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        self.lottery = None
        print(f"Loaded {len(valid)} valid participants.")

    def menu_list(self) -> None:
        while True:
            print("\n-- List Management --\n1. Load default list\n2. Upload custom txt list\n"
                  "3. View groups\n4. View participants\n5. Remove a participant\n0. Back")
            c = input("> ").strip()
            if c == "1":
                self._accept_list(*self.list_manager.load_default_list())
            elif c == "2":
                path = input("Path of txt file (each line 'Name,Department Group'): ").strip()
                self._accept_list(*self.list_manager.load_custom_list(path))
            elif c == "3":
                info = self.list_manager.get_group_info(self.users)
                if not info:
                    print("No list loaded.")
                for i, (g, n) in enumerate(info.items(), 1):
                    print(f"  {i}. {g}: {n} people")
            elif c == "4":
                for i, u in enumerate(self.users, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            elif c == "5":
                name = input("Name to remove: ").strip()
                before = len(self.users)
                self.users = [u for u in self.users if u.name != name]
                print("Removed." if len(self.users) < before else "Not found.")
                self.lottery = None
            elif c == "0":
                return

    # ---------------------------------------------------------------- prizes
    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            raw = input("Avoidance groups (numbers or names, comma-separated, empty=none): ")
        else:
            raw = input("Avoidance groups (names, comma-separated, empty=none): ")
        result = []
        for part in raw.replace("\uff0c", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                part = groups[int(part) - 1]
            if part not in result:
                result.append(part)
        return result

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | drawer: {p.associated_drawer or 'N/A'} | "
                  f"avoid: {', '.join(p.avoid_groups) or 'None'}")

    def menu_prize(self) -> None:
        while True:
            print("\n-- Prize Configuration --\n1. Load preset prizes\n2. Add custom prize\n"
                  "3. Set avoidance groups\n4. Reorder prizes\n5. View prizes\n"
                  "6. Remove prize\n0. Back")
            c = input("> ").strip()
            try:
                if c == "1":
                    for e in self.prize_manager.load_default_prizes():
                        print("  " + e)
                    self._show_prizes()
                elif c == "2":
                    name = input("Prize name: ")
                    qty = input("Quantity: ")
                    drawer = input("Associated lottery person (empty=none): ").strip() or None
                    groups = self._select_groups()
                    self.prize_manager.add_prize(name, qty, groups, drawer)
                    print("Prize added.")
                elif c == "3":
                    self._show_prizes()
                    idx = int(input("Prize number: "))
                    ok = self.prize_manager.set_avoid_groups(idx, self._select_groups())
                    print("Updated." if ok else "Invalid prize number.")
                elif c == "4":
                    self._show_prizes()
                    raw = input("New order (e.g. 3,1,2): ").replace(" ", ",")
                    order = [int(x) for x in raw.split(",") if x.strip()]
                    print("Reordered." if self.prize_manager.reorder_prizes(order)
                          else "Invalid order.")
                    self._show_prizes()
                elif c == "5":
                    self._show_prizes()
                elif c == "6":
                    self._show_prizes()
                    p = self.prize_manager.remove_prize(int(input("Prize number: ")))
                    print(f"Removed {p.name}." if p else "Invalid prize number.")
                elif c == "0":
                    return
            except ValueError as exc:
                print(f"Error: {exc}")

    # --------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        auto = input("Manual control mode? (y/n, default y): ").strip().lower() == "n"
        reader = None if auto else input
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n===== Round {rnd}: {prize.name} (quantity: {prize.quantity}) =====")
            print("Rules: " + self.lottery.describe_rules(prize))
            results = self.lottery.run_round(prize, reader)
            print(f"--- Results of {prize.name} ---")
            for i, u in enumerate(results, 1):
                print(f"  {i}. {u.name} ({u.department})")
            if not results:
                print("  No winners.")
        self.show_summary()

    def show_summary(self) -> None:
        print("\n===== Complete Winner List =====")
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not any(data.values()):
            print("No winners yet.")
            return
        for name, ws in data.items():
            if not ws:
                continue
            print(f"[{name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {name} - "
                      f"{w.time:%Y-%m-%d %H:%M:%S}")

    def run(self) -> None:
        print("=== Company Team Building Event Smart Lottery System ===")
        while True:
            print("\n1. List management\n2. Prize configuration\n3. Start lottery\n"
                  "4. View results\n5. Export results\n0. Exit")
            c = input("> ").strip()
            if c == "1":
                self.menu_list()
            elif c == "2":
                self.menu_prize()
            elif c == "3":
                self.run_lottery()
            elif c == "4":
                self.show_summary()
            elif c == "5":
                ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
                print(msg)
            elif c == "0":
                print("Goodbye!")
                return


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExited.")


if __name__ == "__main__":
    main()
