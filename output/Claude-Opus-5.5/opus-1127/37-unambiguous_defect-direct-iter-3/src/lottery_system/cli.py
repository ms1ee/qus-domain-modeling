"""Command-line interface for the lottery system."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "exit"


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery = None

    # ---------------------------------------------------------------- lists
    def _accept_list(self, users, errors) -> None:
        valid, dups = self.list_manager.validate_users(users)
        if errors:
            print("Format errors detected:")
            for e in errors:
                print("  " + e)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        if errors or dups:
            choice = ask("Remove invalid data and continue (r) or terminate upload (t)? ").strip().lower()
            if choice != "r":
                print("Upload terminated. Current list unchanged.")
                return
        if not valid:
            print("No valid users loaded.")
            return
        self.users = valid
        self.lottery = None
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def load_custom(self) -> None:
        path = ask("Enter txt file path (format per line: Name,Department): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            return
        self._accept_list(users, errors)

    def show_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for dept, cnt in info.items():
            print(f"  {dept}: {cnt} people")

    # --------------------------------------------------------------- prizes
    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names, comma separated, empty for none): ").strip()
        result = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                g = groups[int(token) - 1]
            else:
                g = token
            if g not in result:
                result.append(g)
        return result

    def add_prize(self) -> None:
        name = ask("Prize name: ").strip()
        qty = ask("Quantity: ").strip()
        avoid = self._select_groups()
        drawer = ask("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print("Prize added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def configure_avoid(self) -> None:
        self.show_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        raw = ask("Prize number to configure: ").strip()
        if not raw.isdigit():
            print("Invalid number.")
            return
        groups = self._select_groups()
        if self.prize_manager.set_avoid_groups(int(raw) - 1, groups):
            print("Avoidance groups updated.")
        else:
            print("Invalid prize number.")

    def reorder(self) -> None:
        self.show_prizes()
        raw = ask("Enter new order as serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Order updated.")
            self.show_prizes()
        else:
            print("Invalid order.")

    # -------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        lm = self.lottery
        print("Commands during the draw: Enter = draw next, 'pause', 'continue', 'terminate'.")
        for idx, prize in enumerate(prizes, 1):
            already = len(self.result_manager.get_round_winners(prize))
            remaining = prize.quantity - already
            if remaining <= 0:
                continue
            print("\n" + "=" * 60)
            print(f"Round {idx}: {prize.name} | Quantity: {prize.quantity}")
            print("Rules: " + lm.describe_rules(prize))
            print("=" * 60)
            lm.start_round(prize)
            paused = False
            drawn = 0
            terminated = False
            while drawn < remaining:
                if paused:
                    cmd = ask("[Paused] Enter 'continue' to resume or 'terminate' to skip: ").strip().lower()
                else:
                    cmd = ask(f"Currently drawing the {already + drawn + 1}th winner (Enter to draw): ").strip().lower()
                if cmd == "exit":
                    terminated = True
                    break
                if cmd == "pause":
                    paused = True
                    print("Lottery paused.")
                    continue
                if cmd == "continue":
                    if paused:
                        print("Lottery resumed.")
                    paused = False
                    continue
                if cmd == "terminate":
                    print("Current round terminated and skipped.")
                    terminated = True
                    break
                if paused:
                    continue
                user = lm.draw_one(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                drawn += 1
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lm.finish_round(prize)
            print(f"\nResults of {prize.name}:")
            for i, w in enumerate(self.result_manager.get_round_winners(prize), 1):
                print(f"  {i}. {w.user.name} ({w.user.department})")
            if terminated and idx < len(prizes):
                nxt = ask("Continue to next round? (y/n): ").strip().lower()
                if nxt not in ("y", "yes", ""):
                    print("Lottery stopped.")
                    return
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not any(grouped.values()):
            print("No winners yet.")
            return
        print("\nComplete winner list:")
        for prize_name, ws in grouped.items():
            if not ws:
                continue
            print(f"[{prize_name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ----------------------------------------------------------------- menu
    def run(self) -> None:
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.show_groups),
            "4": ("Load preset prizes", self._load_default_prizes),
            "5": ("Add custom prize", self.add_prize),
            "6": ("Configure avoidance groups", self.configure_avoid),
            "7": ("Reorder prizes", self.reorder),
            "8": ("View prizes", self.show_prizes),
            "9": ("Start lottery", self.run_lottery),
            "10": ("View results", self.show_summary),
            "11": ("Export results", self.export),
            "0": ("Exit", None),
        }
        print("Company Team Building Event Smart Lottery System")
        while True:
            print()
            for k, (label, _) in actions.items():
                print(f"  {k}. {label}")
            choice = ask("Select: ").strip().lower()
            if choice in ("0", "exit", "quit"):
                print("Bye.")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid choice.")
                continue
            action[1]()

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        self.show_prizes()


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
