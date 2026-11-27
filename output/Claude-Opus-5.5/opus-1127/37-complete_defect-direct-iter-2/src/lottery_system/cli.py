"""Command-line interface for the lottery system."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "0"


class App:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.drawn_prizes = []

    # ---- list -------------------------------------------------------
    def _accept_users(self, users, errors) -> None:
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Problems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            while True:
                c = ask("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").strip().lower()
                if c == "r":
                    break
                if c == "t":
                    print("Upload terminated. Current list unchanged.")
                    return
        if not valid:
            print("No valid users loaded.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} valid users.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_users(users, errors)

    def load_custom(self) -> None:
        path = ask("Enter txt file path (each line 'Name,Department Group'): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("Nothing loaded.")
            return
        self._accept_users(users, errors)

    def view_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")
        print(f"Total: {len(self.users)} people")

    # ---- prizes -----------------------------------------------------
    def load_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")
        self.show_prizes()

    def _choose_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names, comma separated, blank for none): ").strip()
        result: List[str] = []
        for part in raw.replace("\uff0c", ",").split(","):
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

    def add_custom_prize(self) -> None:
        name = ask("Prize name: ").strip()
        qty = ask("Quantity: ").strip()
        drawer = ask("Associated lottery person (blank for none): ").strip() or None
        avoid = self._choose_groups()
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self.show_prizes()
        raw = ask("Select prize number: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            print("Invalid selection.")
            return
        prize = prizes[int(raw) - 1]
        prize.avoid_groups = self._choose_groups()
        print(f"Avoidance groups for '{prize.name}': {', '.join(prize.avoid_groups) or 'None'}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize order:")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | drawer: {p.associated_drawer or '-'} "
                  f"| avoid: {', '.join(p.avoid_groups) or 'None'}")

    def reorder(self) -> None:
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order as serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace("\uff0c", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Order updated.")
            self.show_prizes()
        else:
            print("Invalid order: must contain every serial number exactly once.")

    # ---- lottery ----------------------------------------------------
    def _control(self) -> str:
        """Return 'draw' or 'terminate'."""
        paused = False
        while True:
            prompt = ("[Paused] Type 'continue' or 'terminate': " if paused
                      else "Press Enter to draw ('pause' / 'terminate'): ")
            cmd = ask(prompt).strip().lower()
            if cmd == "terminate":
                return "terminate"
            if paused:
                if cmd == "continue":
                    paused = False
                    print("Lottery resumed.")
                continue
            if cmd == "pause":
                paused = True
                print("Lottery paused.")
                continue
            if cmd in ("", "continue", "draw"):
                return "draw"
            print("Unknown command.")

    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        self.drawn_prizes = prizes
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print(f"Rules: {lottery.describe_rules(prize)}")
            print("=" * 60)
            round_winners: List[User] = []
            for i in range(1, prize.quantity + 1):
                if self._control() == "terminate":
                    print("Current round terminated, skipping.")
                    break
                print(f"Currently drawing the {ordinal(i)} winner...")
                user = lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                if not self.result_manager.add_winner(user, prize):
                    continue
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lottery.record_round(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.drawn_prizes)
        if not any(grouped.values()):
            print("No winners yet.")
            return
        print("\nComplete winner list:")
        print(f"  {'Name':<20}{'Department':<30}Prize")
        for pname, ws in grouped.items():
            for w in ws:
                print(f"  {w.user.name:<20}{w.user.department:<30}{pname}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.drawn_prizes)
        print(msg)

    # ---- main loop --------------------------------------------------
    def run(self) -> None:
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_custom_prize, "6": self.set_avoid_groups,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_results,
            "10": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            print(" 1. Load default list      2. Upload custom txt list")
            print(" 3. View groups            4. Load preset prizes")
            print(" 5. Add custom prize       6. Set prize avoidance groups")
            print(" 7. View / reorder prizes  8. Start lottery")
            print(" 9. View all results      10. Export results")
            print(" 0. Exit")
            choice = ask("Select: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid option.")


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
