"""Command-line interface for the lottery system."""

from typing import List

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
        return input(prompt)
    except EOFError:
        raise SystemExit(0)


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []

    # ---- list -------------------------------------------------------
    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        valid, dups = self.list_manager.validate_users(users)
        for e in errors:
            print("  " + e)
        self.users = valid
        print(f"Default list loaded: {len(valid)} valid participants.")

    def load_custom(self) -> None:
        path = ask("Enter txt file path (format per line: Name,Department Group): ")
        users, errors = self.list_manager.load_custom_list(path)
        if errors and not users and any(e.startswith("File Error") for e in errors):
            for e in errors:
                print("  " + e)
            return
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            print("Invalid data detected:")
            for e in errors:
                print("  " + e)
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            choice = ask("Remove invalid data and continue (y) or terminate upload (n)? ").strip().lower()
            if choice not in ("y", "yes"):
                print("Upload terminated.")
                return
        if not valid:
            print("No valid participants in file. Upload terminated.")
            return
        self.users = valid
        print(f"Custom list loaded: {len(valid)} valid participants.")

    def show_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for i, (dept, cnt) in enumerate(info.items(), 1):
            print(f"  {i}. {dept}: {cnt} people")
        print(f"Total: {len(self.users)} people")

    # ---- prizes -----------------------------------------------------
    def load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Default prizes loaded.")

    def add_custom_prize(self) -> None:
        name = ask("Prize name: ").strip()
        qty = ask("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid: List[str] = []
        if groups:
            print("Available groups:")
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = ask("Avoidance groups (numbers separated by commas, empty for none): ").strip()
            if sel:
                for part in sel.replace("\uff0c", ",").split(","):
                    part = part.strip()
                    if part.isdigit() and 1 <= int(part) <= len(groups):
                        if groups[int(part) - 1] not in avoid:
                            avoid.append(groups[int(part) - 1])
                    elif part:
                        print(f"  Ignored invalid selection: {part}")
        else:
            sel = ask("Avoidance groups (names separated by commas, empty for none): ").strip()
            avoid = [s.strip() for s in sel.split(",") if s.strip()]
        drawer = ask("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p}")

    def reorder(self) -> None:
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("\uff0c", ",").replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered:")
            self.show_prizes()
        else:
            print("Invalid order: must contain each serial number exactly once.")

    # ---- lottery ----------------------------------------------------
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.result_manager.winners:
            c = ask("Previous results exist. Clear them and restart? (y/n): ").strip().lower()
            if c not in ("y", "yes"):
                return
        self.result_manager.clear()
        lm = LotteryManager(self.users)
        print("Commands during drawing: [Enter] draw next, 'pause', 'continue', 'terminate'.")
        for rnd, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {rnd}: {prize.name} | Quantity: {prize.quantity}")
            print("Rules: " + lm.describe_rules(prize))
            print("=" * 60)
            round_winners: List[User] = []
            terminated = False
            i = 1
            while i <= prize.quantity:
                cmd = ask(f"[{ordinal(i)} winner] command: ").strip().lower()
                if cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                    while True:
                        c2 = ask("(paused) > ").strip().lower()
                        if c2 == "continue":
                            print("Lottery resumed.")
                            break
                        if c2 == "terminate":
                            terminated = True
                            break
                        print("Lottery is paused. Type 'continue' or 'terminate'.")
                    if terminated:
                        break
                    continue
                if cmd == "continue":
                    print("Lottery is not paused.")
                    continue
                if cmd == "terminate":
                    terminated = True
                    break
                if cmd not in ("", "draw", "d"):
                    print("Unknown command.")
                    continue
                print(f"Currently drawing the {ordinal(i)} winner...")
                user = lm.draw_next(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                w = self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(str(w))
                i += 1
            if terminated:
                print(f"Round '{prize.name}' terminated and skipped.")
            lm.complete_round(prize, round_winners)
            print(f"--- Results of round {rnd}: {prize.name} ---")
            if round_winners:
                for n, u in enumerate(round_winners, 1):
                    print(f"  {n}. {u.name} ({u.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_results()

    def show_results(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        print("\n===== Complete Winner List =====")
        print(f"{'Name':<20}{'Department':<30}Prize")
        for prize_name, winners in grouped.items():
            for w in winners:
                print(f"{w.user.name:<20}{w.user.department:<30}{prize_name}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    def run(self) -> None:
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.show_groups,
            "4": self.load_default_prizes, "5": self.add_custom_prize,
            "6": self.show_prizes, "7": self.reorder, "8": self.run_lottery,
            "9": self.show_results, "10": self.export,
        }
        while True:
            print("\n===== Team Building Smart Lottery System =====")
            print(" 1. Load default list        2. Upload custom txt list")
            print(" 3. View groups              4. Load preset prizes")
            print(" 5. Add custom prize         6. View prizes")
            print(" 7. Reorder prizes           8. Start lottery")
            print(" 9. View all results        10. Export results")
            print(" 0. Exit")
            choice = ask("Select: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid option.")
                continue
            action()


def main() -> None:
    try:
        LotteryCLI().run()
    except KeyboardInterrupt:
        print("\nExited.")


if __name__ == "__main__":
    main()
