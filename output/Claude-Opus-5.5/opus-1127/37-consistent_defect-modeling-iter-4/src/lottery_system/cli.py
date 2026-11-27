"""Command-line interface for the lottery system."""

import sys

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt=""):
    try:
        return input(prompt).strip()
    except EOFError:
        print("\nInput closed. Exiting.")
        sys.exit(0)


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None
        self.drawn_count = {}
        self.status = "idle"

    # ---------- list ----------
    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        self._set_users(valid)
        print(f"Default list loaded: {len(valid)} participants.")

    def load_custom(self):
        path = ask("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        if errors:
            print("Problems detected:")
            for e in errors:
                print("  " + e)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        if not valid:
            print("No valid participants found. Upload terminated.")
            return
        if errors or dups:
            choice = ask("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
            if choice != "r":
                print("Upload terminated.")
                return
        self._set_users(valid)
        print(f"Custom list loaded: {len(valid)} participants.")

    def _set_users(self, users):
        self.users = users
        prior = [w.user for w in self.result_manager.winners]
        self.lottery = LotteryManager(users, existing_winners=prior)

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        print("Valid groups:")
        for g, c in self.list_manager.get_group_info(self.users).items():
            print(f"  {g}: {c} people")

    # ---------- prizes ----------
    def load_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def _choose_groups(self):
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if not groups:
            raw = ask("Enter avoidance groups separated by ',' (blank for none): ")
            return [g.strip() for g in raw.split(",") if g.strip()]
        for i, g in enumerate(groups, 1):
            print(f"  {i}. {g}")
        raw = ask("Select avoidance groups by number, separated by ',' (blank for none): ")
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(groups):
                if groups[int(part) - 1] not in selected:
                    selected.append(groups[int(part) - 1])
            elif part:
                print(f"  Ignored invalid selection: {part}")
        return selected

    def add_prize(self):
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        drawer = ask("Associated lottery person (blank for none): ") or None
        groups = self._choose_groups()
        if self.prize_manager.add_prize(name, qty, groups, drawer):
            print("Prize added.")
        else:
            print("Failed to add prize (empty/duplicate name or invalid quantity).")

    def configure_avoidance(self):
        prizes = self.view_prizes()
        if not prizes:
            return
        idx = ask("Select prize number: ")
        if not idx.isdigit() or not 1 <= int(idx) <= len(prizes):
            print("Invalid selection.")
            return
        groups = self._choose_groups()
        self.prize_manager.set_avoid_groups(int(idx) - 1, groups)
        print("Avoidance groups updated.")

    def reorder(self):
        prizes = self.view_prizes()
        if not prizes:
            return
        raw = ask("Enter new order of serial numbers separated by ',' (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace(" ", "").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order.")

    def view_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")
        return prizes

    # ---------- lottery ----------
    def _control(self):
        """Return 'go' or 'terminate'."""
        cmd = ask("[Enter]=draw | pause | terminate > ").lower()
        if cmd == "terminate":
            return "terminate"
        if cmd == "pause":
            self.status = "paused"
            print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
            while True:
                c = ask("> ").lower()
                if c == "continue":
                    self.status = "running"
                    print("Resumed.")
                    return "go"
                if c == "terminate":
                    return "terminate"
        return "go"

    def run_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        self.status = "running"
        for rnd, prize in enumerate(prizes, 1):
            done = self.drawn_count.get(prize.name, 0)
            remaining = prize.quantity - done
            if remaining <= 0:
                continue
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {remaining}")
            print("Rules: " + self.lottery.describe_rules(prize))
            print("=" * 60)
            round_winners = []
            for i in range(remaining):
                if self._control() == "terminate":
                    print("Current round terminated, skipping.")
                    break
                print(f"Currently drawing the {done + i + 1}th winner...")
                winner = self.lottery.draw_winner(prize)
                if winner is None:
                    print("No eligible participants left for this prize.")
                    break
                self.result_manager.add_winner(winner, prize)
                round_winners.append(winner)
                self.drawn_count[prize.name] = self.drawn_count.get(prize.name, 0) + 1
                print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")
            self.lottery.finish_round(prize, round_winners)
            print(f"\nRound {rnd} results ({prize.name}):")
            if not round_winners:
                print("  (none)")
            for n, w in enumerate(round_winners, 1):
                print(f"  {n}. {w.name} ({w.department})")
        self.status = "finished"
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for pname, winners in data.items():
            if not winners:
                continue
            print(f"[{pname}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {pname} - "
                      f"{w.time.strftime('%Y-%m-%d %H:%M:%S')}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self):
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.configure_avoidance,
            "7": self.reorder, "8": self.view_prizes, "9": self.run_lottery,
            "10": self.show_summary, "11": self.export,
        }
        while True:
            print("""
===== Team Building Smart Lottery System =====
 1. Load default list          2. Upload custom txt list
 3. View groups                4. Load preset prizes
 5. Add custom prize           6. Configure avoidance groups
 7. Reorder prizes             8. View prizes
 9. Start lottery             10. View winner summary
11. Export results             0. Exit""")
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
    LotteryCLI().run()


if __name__ == "__main__":
    main()
