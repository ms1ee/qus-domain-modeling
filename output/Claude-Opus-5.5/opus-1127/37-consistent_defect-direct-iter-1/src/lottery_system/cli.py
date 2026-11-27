"""Command-line interface of the lottery system."""

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise SystemExit(0)


class LotteryApp:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None
        self.finished_rounds = set()

    # ------------------------------------------------------------------- lists
    def _set_users(self, users) -> None:
        self.users = list(users)
        self.lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        self.finished_rounds = set()
        print(f"{len(self.users)} valid participants loaded.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        for e in errors:
            print("  " + e)
        valid, dups = self.list_manager.validate_users(users)
        self._set_users(valid)

    def upload_custom(self) -> None:
        path = ask("Enter txt list path (each line 'Name,Department Group'): ")
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Problems detected in the list:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate name: {d.name} ({d.department})")
            if not valid:
                print("No valid data. Upload terminated.")
                return
            choice = ask("Input 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
            if choice != "r":
                print("Upload terminated.")
                return
        if not valid:
            print("No valid data found. Upload terminated.")
            return
        self._set_users(valid)

    def show_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Valid groups:")
        for i, (dept, cnt) in enumerate(info.items(), 1):
            print(f"  {i}. {dept}: {cnt} people")

    # ------------------------------------------------------------------ prizes
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")

    def add_custom_prize(self) -> None:
        name = ask("Prize name: ")
        qty = ask("Quantity: ")
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            print("Groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names separated by commas, empty for none): ")
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                avoid.append(groups[int(part) - 1])
            else:
                avoid.append(part)
        drawer = ask("Associated lottery person (empty for none): ")
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer or None)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) or "none"
            status = " [done]" if p.name in self.finished_rounds else ""
            print(f"  {i}. {p.name} x{p.quantity} | avoid: {avoid} | "
                  f"drawer: {p.associated_drawer or '-'}{status}")

    def reorder(self) -> None:
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.show_prizes()
        else:
            print("Invalid order: must be a permutation of all serial numbers.")

    # ----------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users or self.lottery is None:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        pending = [p for p in prizes if p.name not in self.finished_rounds]
        if not pending:
            print("All rounds have been completed.")
        for prize in pending:
            self._run_round(prize)
        if all(p.name in self.finished_rounds for p in prizes):
            print("\nAll rounds completed.")
            self.show_summary()

    def _run_round(self, prize) -> None:
        print("\n" + "=" * 60)
        print(f"Round: {prize.name} | Quantity: {prize.quantity}")
        for line in self.lottery.describe_rules(prize):
            print("  Rule: " + line)
        print("Commands: Enter=draw next, 'auto'=draw remaining, 'pause', 'continue', 'terminate'")
        round_winners = []
        idx = 1
        paused = False
        auto = False
        while idx <= prize.quantity:
            if paused:
                cmd = ask("[Paused] input 'continue' to resume or 'terminate' to end this round: ").lower()
                if cmd == "continue":
                    paused = False
                    print("Lottery resumed.")
                elif cmd == "terminate":
                    print("Round terminated.")
                    break
                else:
                    print("Lottery is paused.")
                continue
            if not auto:
                cmd = ask(f"Next: {ordinal(idx)} winner > ").lower()
                if cmd == "pause":
                    paused = True
                    print("Lottery paused.")
                    continue
                if cmd == "terminate":
                    print("Round terminated.")
                    break
                if cmd == "auto":
                    auto = True
                elif cmd not in ("", "draw", "next", "continue"):
                    print("Unknown command.")
                    continue
            print(f"Currently drawing the {ordinal(idx)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible participants left for this prize.")
                break
            winner = self.result_manager.add_winner(user, prize)
            if winner is None:
                print("Duplicate winner detected, skipped.")
                continue
            print(str(winner))
            round_winners.append(user)
            idx += 1
        self.lottery.record_round_result(prize, round_winners)
        self.finished_rounds.add(prize.name)
        print(f"--- Results of {prize.name} ---")
        if not round_winners:
            print("  (no winners)")
        for i, u in enumerate(round_winners, 1):
            print(f"  {i}. {u.name} ({u.department})")

    def show_summary(self) -> None:
        data = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not any(data.values()):
            print("No winners yet.")
            return
        for name, items in data.items():
            print(f"[{name}]")
            for w in items:
                print(f"  {w.user.name} ({w.user.department}) - {name} - "
                      f"{w.win_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # --------------------------------------------------------------------- run
    def run(self) -> None:
        actions = {
            "1": ("Load default list", self.load_default),
            "2": ("Upload custom txt list", self.upload_custom),
            "3": ("View groups", self.show_groups),
            "4": ("Load preset prizes", self.load_default_prizes),
            "5": ("Add custom prize", self.add_custom_prize),
            "6": ("View prizes", self.show_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.start_lottery),
            "9": ("View winner summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        print("=== Team Building Smart Lottery System ===")
        while True:
            print()
            for key, (label, _) in actions.items():
                print(f"{key}. {label}")
            print("0. Exit")
            choice = ask("Select: ")
            if choice == "0":
                print("Bye.")
                return
            action = actions.get(choice)
            if action:
                action[1]()
            else:
                print("Invalid choice.")


def main() -> None:
    LotteryApp().run()


if __name__ == "__main__":
    main()
