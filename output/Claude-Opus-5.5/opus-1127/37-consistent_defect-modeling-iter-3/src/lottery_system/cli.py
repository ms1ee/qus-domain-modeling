"""Command-line interface."""
from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "0"


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager: LotteryManager = None

    # ---------- list ----------
    def _set_users(self, users):
        self.users = users
        self.result_manager = ResultManager()
        self.lottery_manager = LotteryManager(users, self.result_manager)
        print(f"{len(users)} valid participants loaded.")

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        for e in errors:
            print("  " + e)
        valid, _ = self.list_manager.validate_users(users)
        self._set_users(valid)

    def load_custom(self):
        path = _ask("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        if errors and not users:
            for e in errors:
                print("  " + e)
            print("Upload failed.")
            return
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Validation issues detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            while True:
                choice = _ask("[r] remove all invalid data and continue, "
                              "[m] manually review entries, [t] terminate upload: ").lower()
                if choice == "t":
                    print("Upload terminated.")
                    return
                if choice == "r":
                    break
                if choice == "m":
                    valid = self._manual_review(users)
                    break
        self._set_users(valid)

    def _manual_review(self, users):
        current = list(users)
        while True:
            print("Current entries:")
            names = {}
            for i, u in enumerate(current, 1):
                names[u.name] = names.get(u.name, 0) + 1
            for i, u in enumerate(current, 1):
                mark = " [DUPLICATE]" if names[u.name] > 1 else ""
                print(f"  {i}. {u.name} ({u.department}){mark}")
            s = _ask("Enter serial numbers to remove (comma separated), or press Enter to finish: ")
            if not s:
                break
            try:
                idxs = sorted({int(x) for x in s.replace("，", ",").split(",") if x.strip()},
                              reverse=True)
            except ValueError:
                print("Invalid input.")
                continue
            for i in idxs:
                if 1 <= i <= len(current):
                    current.pop(i - 1)
        valid, dups = self.list_manager.validate_users(current)
        if dups:
            print(f"{len(dups)} remaining duplicates removed automatically.")
        return valid

    def view_groups(self):
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for g, c in info.items():
            print(f"  {g}: {c} people")

    # ---------- prizes ----------
    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def _choose_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        s = _ask("Avoidance groups (serial numbers or names, comma separated, Enter for none): ")
        result = []
        for tok in s.replace("，", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.isdigit() and 1 <= int(tok) <= len(groups):
                g = groups[int(tok) - 1]
            else:
                g = tok
            if g not in result:
                result.append(g)
        return result

    def add_prize(self):
        name = _ask("Prize name: ")
        qty = _ask("Quantity: ")
        groups = self._choose_groups()
        drawer = _ask("Associated lottery person (Enter for none): ") or None
        try:
            p = self.prize_manager.add_prize(name, qty, groups, drawer)
            print(f"Prize '{p.name}' added.")
        except ValueError as e:
            print(f"Error: {e}")

    def configure_prize(self):
        self.show_prizes()
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            return
        s = _ask("Select prize serial number to configure: ")
        if not s.isdigit() or not 1 <= int(s) <= len(prizes):
            print("Invalid selection.")
            return
        idx = int(s) - 1
        self.prize_manager.set_avoid_groups(idx, self._choose_groups())
        drawer = _ask("Associated lottery person (Enter to keep current, '-' to clear): ")
        if drawer == "-":
            self.prize_manager.set_drawer(idx, None)
        elif drawer:
            self.prize_manager.set_drawer(idx, drawer)
        print("Prize updated.")

    def reorder(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        s = _ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in s.replace("，", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.show_prizes()
        else:
            print("Invalid order.")

    # ---------- lottery ----------
    def run_lottery(self):
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        lm = self.lottery_manager
        for rnd, prize in enumerate(prizes, 1):
            if lm.is_completed(prize):
                continue
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print(f"Rules: {prize.rule_description()}")
            if lm.is_fallback_active(prize):
                print("Fallback triggered: prize pool limited to Cheng Ru Group members!")
            print("Commands: Enter=draw next, 'pause', 'continue', 'terminate'")
            round_winners: List[User] = []
            terminated = False
            while lm.remaining(prize) > 0:
                cmd = _ask(f"[{prize.name}] > ").lower()
                if cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                    while True:
                        c = _ask("(paused) > ").lower()
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
                if cmd not in ("", "continue", "draw"):
                    print("Unknown command.")
                    continue
                n = len(round_winners) + 1
                print(f"Currently drawing the {n}th winner...")
                user = lm.draw_winner(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            if terminated:
                print("Current round terminated and skipped.")
            lm.finish_round(prize, round_winners)
            print(f"--- Results of round {rnd}: {prize.name} ---")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self):
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("=" * 60)
        print("Complete winner list (prize level high to low):")
        any_w = False
        for pname, winners in grouped.items():
            if not winners:
                continue
            any_w = True
            print(f"[{pname}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {pname} - "
                      f"{w.winning_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if not any_w:
            print("  No winners yet.")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------- main loop ----------
    def run(self):
        actions = {
            "1": self.load_default,
            "2": self.load_custom,
            "3": self.view_groups,
            "4": self._load_default_prizes,
            "5": self.add_prize,
            "6": self.configure_prize,
            "7": self.show_prizes,
            "8": self.reorder,
            "9": self.run_lottery,
            "10": self.show_results,
            "11": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            print(" 1. Load default list        2. Upload custom list")
            print(" 3. View groups              4. Load preset prizes")
            print(" 5. Add custom prize         6. Configure prize rules")
            print(" 7. View prizes              8. Reorder prizes")
            print(" 9. Start lottery           10. View results")
            print("11. Export results           0. Exit")
            choice = _ask("Select: ")
            if choice == "0":
                print("Bye.")
                return
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice.")

    def _load_default_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        self.show_prizes()


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
