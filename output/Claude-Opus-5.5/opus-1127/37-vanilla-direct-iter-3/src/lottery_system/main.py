"""Command-line interface of the lottery system."""
from typing import List, Optional

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _input(prompt: str) -> Optional[str]:
    try:
        return input(prompt)
    except EOFError:
        return None


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.running = True

    # ---------- list ----------
    def load_default_list(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        self.users = valid
        for e in errors:
            print("  " + e)
        print(f"Default list loaded: {len(valid)} participants.")

    def load_custom_list(self):
        path = _input("Enter txt list path: ")
        if path is None:
            return
        users, errors = self.list_manager.load_custom_list(path.strip().strip('"'))
        valid, dups = self.list_manager.validate_users(users)
        if errors:
            print("Problems found:")
            for e in errors:
                print("  " + e)
        if dups:
            print("Duplicate names found:")
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
        if not valid:
            print("No valid participants loaded. Upload terminated.")
            return
        if errors or dups:
            while True:
                choice = _input("[1] Remove invalid data and continue  [2] Terminate upload: ")
                if choice is None or choice.strip() == "2":
                    print("Upload terminated. Current list unchanged.")
                    return
                if choice.strip() == "1":
                    break
                print("Invalid choice.")
        self.users = valid
        print(f"Custom list loaded: {len(valid)} participants.")

    def show_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Valid groups ({len(info)}):")
        for dept, count in info.items():
            print(f"  {dept}: {count} people")
        print(f"Total: {len(self.users)} people")

    def remove_participant(self):
        if not self.users:
            print("No list loaded.")
            return
        for i, u in enumerate(self.users, 1):
            print(f"  {i}. {u}")
        s = _input("Enter number(s) to remove (comma separated): ")
        if not s:
            return
        try:
            idx = sorted({int(x) for x in s.replace("，", ",").split(",") if x.strip()}, reverse=True)
        except ValueError:
            print("Invalid input.")
            return
        for i in idx:
            if 1 <= i <= len(self.users):
                print(f"Removed {self.users.pop(i - 1)}")

    # ---------- prizes ----------
    def _groups(self) -> List[str]:
        return list(self.list_manager.get_group_info(self.users).keys())

    def _select_groups(self) -> List[str]:
        groups = self._groups()
        if not groups:
            s = _input("Enter avoidance groups (comma separated, empty for none): ") or ""
            return [g.strip() for g in s.replace("，", ",").split(",") if g.strip()]
        for i, g in enumerate(groups, 1):
            print(f"  {i}. {g}")
        s = _input("Select avoidance groups by number (comma separated, empty for none): ") or ""
        selected = []
        for x in s.replace("，", ",").split(","):
            x = x.strip()
            if not x:
                continue
            if x.isdigit() and 1 <= int(x) <= len(groups):
                if groups[int(x) - 1] not in selected:
                    selected.append(groups[int(x) - 1])
            else:
                print(f"  Ignored invalid selection: {x}")
        return selected

    def load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")
        self.show_prizes()

    def add_prize(self):
        name = _input("Prize name: ")
        if not name:
            print("Cancelled.")
            return
        qty = _input("Quantity: ") or ""
        drawer = (_input("Associated lottery person (empty for none): ") or "").strip() or None
        groups = self._select_groups()
        try:
            self.prize_manager.add_prize(name, qty.strip(), groups, drawer)
            print("Prize added.")
        except ValueError as e:
            print(f"Error: {e}")

    def configure_avoidance(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.show_prizes()
        s = (_input("Select prize number: ") or "").strip()
        if not s.isdigit() or not 1 <= int(s) <= len(prizes):
            print("Invalid selection.")
            return
        prize = prizes[int(s) - 1]
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoidance groups for '{prize.name}': {', '.join(groups) or 'none'}")

    def reorder_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.show_prizes()
        s = _input("Enter new order as serial numbers (e.g. 3,1,2): ") or ""
        try:
            order = [int(x) for x in s.replace("，", ",").replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.show_prizes()
        else:
            print("Invalid order: must contain each serial number exactly once.")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize rounds:")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    # ---------- lottery ----------
    @staticmethod
    def _wait_command(position: int) -> str:
        paused = False
        while True:
            if paused:
                prompt = "[Paused] Input 'continue' to resume or 'terminate' to skip round: "
            else:
                prompt = (f"Currently drawing the {position}th winner - press Enter to draw "
                          "('pause' / 'terminate' / 'auto'): ")
            cmd = _input(prompt)
            if cmd is None:
                return "terminate"
            cmd = cmd.strip().lower()
            if cmd == "terminate":
                return "terminate"
            if paused:
                if cmd == "continue":
                    paused = False
                    print("Lottery resumed.")
                else:
                    print("Lottery is paused.")
                continue
            if cmd in ("", "draw", "d"):
                return "draw"
            if cmd == "auto":
                return "auto"
            if cmd == "pause":
                paused = True
                print("Lottery paused.")
            elif cmd == "continue":
                print("Lottery is not paused.")
            else:
                print("Unknown command.")

    def start_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.result_manager.winners:
            c = (_input("Existing results will be cleared. Continue? (y/n): ") or "").strip().lower()
            if c != "y":
                return
        self.result_manager.clear()
        lm = LotteryManager(self.users)
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}"
                  + (f" | Lottery person: {prize.associated_drawer}" if prize.associated_drawer else ""))
            print(f"Rules: {lm.describe_rules(prize)}")
            print("=" * 60)
            round_winners = []
            auto = False
            for i in range(1, prize.quantity + 1):
                if not lm._get_eligible_pool(prize):
                    print("No eligible participants remain for this prize. Round ended.")
                    break
                if auto:
                    print(f"Currently drawing the {i}th winner...")
                else:
                    cmd = self._wait_command(i)
                    if cmd == "terminate":
                        print("Current round terminated.")
                        break
                    if cmd == "auto":
                        auto = True
                user = lm.draw_winner(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lm.record_round_result(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self):
        if not self.result_manager.winners:
            print("No results yet.")
            return
        print("\n===== Complete Winner List =====")
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        for name, winners in grouped.items():
            print(f"[{name}]")
            if not winners:
                print("  (none)")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {name} - {w.time_str}")

    def export_results(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------- loop ----------
    def run(self):
        actions = {
            "1": ("Load default list", self.load_default_list),
            "2": ("Upload custom txt list", self.load_custom_list),
            "3": ("View groups", self.show_groups),
            "4": ("Remove participants", self.remove_participant),
            "5": ("Load preset prizes", self.load_default_prizes),
            "6": ("Add custom prize", self.add_prize),
            "7": ("Configure avoidance groups", self.configure_avoidance),
            "8": ("Reorder prizes", self.reorder_prizes),
            "9": ("View prizes", self.show_prizes),
            "10": ("Start lottery", self.start_lottery),
            "11": ("View results", self.show_results),
            "12": ("Export results", self.export_results),
        }
        print("Company Team Building Event Smart Lottery System")
        while self.running:
            print("\n----- Menu -----")
            for k, (label, _) in actions.items():
                print(f"  {k}. {label}")
            print("  0. Exit")
            choice = _input("Select: ")
            if choice is None or choice.strip() == "0":
                print("Goodbye!")
                break
            action = actions.get(choice.strip())
            if action:
                action[1]()
            else:
                print("Invalid choice.")


def main():
    try:
        LotteryApp().run()
    except KeyboardInterrupt:
        print("\nExited.")


if __name__ == "__main__":
    main()
