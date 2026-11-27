"""Command-line interface for the lottery system."""

from __future__ import annotations

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
        return "exit"


class LotteryApp:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = LotteryManager([], self.result_manager)
        self.running = True

    # ---------------------------------------------------------------- list
    def _set_users(self, users) -> None:
        self.users = users
        self.result_manager.clear()
        self.lottery = LotteryManager(users, self.result_manager)
        print(f"{len(users)} valid participants loaded.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        for e in errors:
            print(e)
        valid, dups = self.list_manager.validate_users(users)
        for d in dups:
            print(f"Duplicate name removed: {d.name} ({d.department})")
        self._set_users(valid)

    def load_custom(self) -> None:
        path = ask("Enter txt file path: ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        if errors:
            print("Problems found:")
            for e in errors:
                print("  " + e)
        if dups:
            print("Duplicate names found:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
        if not users and errors:
            print("No valid data loaded.")
            return
        if errors or dups:
            choice = ask("Type 'remove' to remove invalid data and continue, "
                         "or 'terminate' to cancel upload: ").strip().lower()
            if choice not in ("remove", "r"):
                print("Upload terminated.")
                return
        self._set_users(valid)

    def view_groups(self) -> None:
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Department groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # ---------------------------------------------------------------- prizes
    def load_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print(e)
        print("Preset prizes loaded.")

    def add_prize(self) -> None:
        name = ask("Prize name: ").strip()
        qty = ask("Quantity: ").strip()
        drawer = ask("Associated lottery person (empty for none): ").strip() or None
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = ask("Avoidance group numbers, comma separated (empty for none): ").strip()
            for part in sel.replace("，", ",").split(","):
                part = part.strip()
                if not part:
                    continue
                if part.isdigit() and 1 <= int(part) <= len(groups):
                    avoid.append(groups[int(part) - 1])
                else:
                    print(f"Ignored invalid selection: {part}")
        else:
            sel = ask("Avoidance group names, comma separated (empty for none): ").strip()
            avoid = [p.strip() for p in sel.split(",") if p.strip()]
        try:
            prize = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize added: {prize.name}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.describe_rules()}")

    def reorder(self) -> None:
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("New order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order, unchanged.")

    # ---------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        print("Commands during draw: Enter=draw next, 'pause', 'continue', 'terminate'.")
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n===== Round {rnd}: {prize.name} (Quantity: {prize.quantity}) =====")
            print(f"Rules: {prize.describe_rules()}")
            if self.lottery.is_fallback_active(prize):
                print("Fallback triggered: prize pool limited to Cheng Ru group members.")
            round_winners = []
            terminated = False
            for i in range(1, prize.quantity + 1):
                cmd = ask(f"[Enter] draw {ordinal(i)} winner > ").strip().lower()
                if cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip.")
                    while True:
                        cmd = ask("(paused) > ").strip().lower()
                        if cmd in ("continue", "terminate", "exit"):
                            break
                if cmd in ("terminate", "exit"):
                    print("Current round terminated.")
                    terminated = True
                    break
                print(f"Currently drawing the {ordinal(i)} winner...")
                user = self.lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants left for this prize.")
                    break
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.finish_round(prize, round_winners)
            print(f"--- Round {rnd} results ---")
            if round_winners:
                for i, u in enumerate(round_winners, 1):
                    print(f"  {i}. {u.name} ({u.department}) - {prize.name}")
            else:
                print("  No winners.")
            if terminated and cmd == "exit":
                break
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for prize_name, winners in grouped.items():
            print(f"[{prize_name}]")
            if not winners:
                print("  (none)")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} - {w.time_str}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------------------------------------------------------------- main loop
    def run(self) -> None:
        actions = {
            "1": self.load_default,
            "2": self.load_custom,
            "3": self.view_groups,
            "4": self.load_prizes,
            "5": self.add_prize,
            "6": self.view_prizes,
            "7": self.reorder,
            "8": self.run_lottery,
            "9": self.show_summary,
            "10": self.export,
        }
        while self.running:
            print("\n==== Team Building Smart Lottery System ====")
            print("1. Load default list      2. Upload custom list")
            print("3. View groups            4. Load preset prizes")
            print("5. Add custom prize       6. View prizes")
            print("7. Reorder prizes         8. Start lottery")
            print("9. View winner summary    10. Export results")
            print("0. Exit")
            choice = ask("Select: ").strip().lower()
            if choice in ("0", "exit", "quit"):
                print("Goodbye!")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid option.")


def main() -> None:
    LotteryApp().run()


if __name__ == "__main__":
    main()
