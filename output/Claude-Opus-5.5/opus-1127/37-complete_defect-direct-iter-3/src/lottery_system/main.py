"""Command-line interface for the lottery system."""
from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "0"


class App:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []

    # ---------------- list ----------------
    def _accept_list(self, users, errors):
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("\nInvalid data detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = ask("Remove invalid data and continue (r) or terminate upload (t)? ").lower()
            if choice != "r":
                print("Upload terminated. Current list unchanged.")
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
            return
        self._accept_list(users, errors)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")
        print(f"Total: {len(self.users)} people")

    # ---------------- prizes ----------------
    def load_preset_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")

    def add_custom_prize(self):
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid: List[str] = []
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names, comma-separated, blank for none): ")
        for token in raw.replace("\uff0c", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                avoid.append(groups[int(token) - 1])
            else:
                avoid.append(token)
        drawer = ask("Associated lottery person (blank for none): ")
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer or None)
            print(f"Prize '{p.name}' added.")
        except ValueError as e:
            print(f"Error: {e}")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize order:")
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) if p.avoid_groups else "None"
            drawer = p.associated_drawer or "None"
            print(f"  {i}. {p.name} x{p.quantity} | Avoid: {avoid} | Drawer: {drawer}")

    def reorder(self):
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.view_prizes()
        else:
            print("Invalid order. Must be a permutation of all serial numbers.")

    # ---------------- lottery ----------------
    def start_lottery(self):
        prizes = self.prize_manager.get_prizes()
        if not self.users:
            print("Please load a participant list first.")
            return
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.result_manager.winners:
            if ask("Previous results exist and will be cleared. Continue? (y/n): ").lower() != "y":
                return
        self.result_manager = ResultManager()
        engine = LotteryManager(self.users)

        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print("Rules: " + engine.describe_rules(prize))
            print("=" * 60)
            round_winners: List[User] = []
            terminated = False
            x = 1
            while x <= prize.quantity:
                cmd = ask(f"[Enter]=draw winner #{x}, 'pause', 'terminate': ").lower()
                if cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                    while True:
                        c = ask("> ").lower()
                        if c == "continue":
                            print("Lottery resumed.")
                            break
                        if c == "terminate":
                            terminated = True
                            break
                    if terminated:
                        break
                    continue
                if cmd == "terminate":
                    terminated = True
                    break
                if cmd == "0":
                    terminated = True
                    break
                print(f"Currently drawing the {x}th winner...")
                user = engine.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
                x += 1
            if terminated:
                print("Current round terminated and skipped.")
            engine.finish_round(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for pname, ws in grouped.items():
            for w in ws:
                print(f"  {w.user.name} | {w.user.department} | {pname}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_default,
            "2": self.load_custom,
            "3": self.view_groups,
            "4": self.load_preset_prizes,
            "5": self.add_custom_prize,
            "6": self.view_prizes,
            "7": self.reorder,
            "8": self.start_lottery,
            "9": self.show_summary,
            "10": self.export,
        }
        while True:
            print(
                "\n=== Team Building Smart Lottery ===\n"
                " 1. Load default list\n 2. Upload custom list\n 3. View groups\n"
                " 4. Load preset prizes\n 5. Add custom prize\n 6. View prizes\n"
                " 7. Reorder prizes\n 8. Start lottery\n 9. View winner list\n"
                "10. Export results\n 0. Exit"
            )
            choice = ask("Select: ")
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid option.")


def main():
    App().run()


if __name__ == "__main__":
    main()
