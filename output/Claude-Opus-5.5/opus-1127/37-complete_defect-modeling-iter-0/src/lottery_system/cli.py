"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt: str, default: str = "") -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return default


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryApp:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: List[User] = []
        self.result_manager = ResultManager()
        self.state = "IDLE"
        self.current_round_index = 0

    # ---------------------------------------------------------------- lists
    def _accept_list(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Validation issues detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate name: {d.name} ({d.department})")
            choice = ask("Remove invalid data and continue (r) or terminate upload (t)? [r/t]: ", "t").lower()
            if choice != "r":
                print("Upload terminated. List unchanged.")
                return
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def load_custom(self):
        path = ask("Enter txt file path (each line 'Name,Department Group'): ")
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("No valid data loaded.")
            return
        self._accept_list(users, errors)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Valid groups ({len(info)}):")
        for g, c in info.items():
            print(f"  {g}: {c} people")

    # --------------------------------------------------------------- prizes
    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) or "None"
            print(f"  {i}. {p.name} x{p.quantity} | Drawer: {p.associated_drawer or 'None'} | Avoid: {avoid}")

    def load_preset_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        self.show_prizes()

    def add_custom_prize(self):
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        drawer = ask("Associated lottery person (optional): ")
        avoid = self._select_groups()
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer or None)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            raw = ask("Select avoidance groups by number (comma separated, blank for none): ")
        else:
            raw = ask("Enter avoidance group names (comma separated, blank for none): ")
        result = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                result.append(groups[int(token) - 1])
            elif not token.isdigit():
                result.append(token)
            else:
                print(f"Ignored invalid selection: {token}")
        return result

    def configure_avoidance(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        idx = ask("Select prize number: ")
        if not idx.isdigit():
            print("Invalid number.")
            return
        groups = self._select_groups()
        if self.prize_manager.set_avoid_groups(int(idx) - 1, groups):
            print("Avoidance groups updated.")
        else:
            print("Invalid prize number.")

    def reorder(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Order updated.")
            self.show_prizes()
        else:
            print("Invalid order.")

    # -------------------------------------------------------------- lottery
    def start_lottery(self):
        prizes = self.prize_manager.get_prizes()
        if not self.users:
            print("Please load a participant list first.")
            return
        if not prizes:
            print("Please configure prizes first.")
            return
        engine = LotteryManager(self.users)
        self.result_manager = ResultManager()
        self.state = "RUNNING"
        print("Commands during draw: Enter=draw next, 'auto'=draw remaining, "
              "'pause', 'continue', 'terminate'.")
        for r, prize in enumerate(prizes, 1):
            self.current_round_index = r
            print(f"\n=== Round {r}: {prize.name} | Quantity: {prize.quantity} ===")
            print("Rules: " + engine.get_rule_description(prize))
            round_winners = []
            auto = False
            terminated = False
            i = 0
            while i < prize.quantity:
                if not auto:
                    cmd = ask(f"[{ordinal(i + 1)} draw] > ", "auto").lower()
                    if cmd == "pause":
                        self.state = "PAUSED"
                        print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                        while True:
                            c = ask("(paused) > ", "terminate").lower()
                            if c == "continue":
                                self.state = "RUNNING"
                                print("Lottery resumed.")
                                break
                            if c == "terminate":
                                cmd = "terminate"
                                break
                            print("Lottery is paused.")
                        if cmd != "terminate":
                            continue
                    if cmd == "terminate":
                        self.state = "RUNNING"
                        print("Current round terminated and skipped.")
                        terminated = True
                        break
                    if cmd == "auto":
                        auto = True
                    elif cmd not in ("", "continue", "draw"):
                        print("Unknown command.")
                        continue
                print(f"Currently drawing the {ordinal(i + 1)} winner...")
                winner = engine.draw_winner(prize)
                if winner is None:
                    print("No eligible participants left for this prize.")
                    break
                round_winners.append(winner)
                self.result_manager.add_winner(winner, prize)
                print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")
                i += 1
            engine.record_round_result(prize, round_winners)
            print(f"--- Round {r} results{' (terminated)' if terminated else ''} ---")
            if not round_winners:
                print("  No winners.")
            for n, w in enumerate(round_winners, 1):
                print(f"  {n}. {w.name} ({w.department})")
        self.state = "FINISHED"
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        print("===== Complete Winner List =====")
        for name, ws in grouped.items():
            for w in ws:
                print(f"  {w.user.name} | {w.user.department} | {name}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ----------------------------------------------------------------- menu
    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_preset_prizes, "5": self.add_custom_prize,
            "6": self.configure_avoidance, "7": self.reorder, "8": self.show_prizes,
            "9": self.start_lottery, "10": self.show_results, "11": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            print(" 1. Load default list        2. Upload custom txt list")
            print(" 3. View groups              4. Load preset prizes")
            print(" 5. Add custom prize         6. Configure avoidance groups")
            print(" 7. Reorder prizes           8. View prizes")
            print(" 9. Start lottery           10. View all results")
            print("11. Export results           0. Exit")
            choice = ask("Select: ", "0")
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice.")


def main():
    LotteryApp().run()


if __name__ == "__main__":
    main()
