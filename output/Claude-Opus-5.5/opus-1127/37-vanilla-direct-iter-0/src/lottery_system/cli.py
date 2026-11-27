"""Command-line interface of the lottery system."""

from __future__ import annotations

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


class LotteryCLI:
    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self.out = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery = None
        self.completed = set()

    def ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    # ------------------------------------------------------------- main menu
    def run(self) -> None:
        self.out("=" * 60)
        self.out(" Company Team Building Event Smart Lottery System")
        self.out("=" * 60)
        try:
            while True:
                self.out("\nMain Menu:")
                self.out(" 1. List management")
                self.out(" 2. Prize configuration")
                self.out(" 3. Start lottery")
                self.out(" 4. View results summary")
                self.out(" 5. Export results")
                self.out(" 0. Exit")
                choice = self.ask("Select: ")
                if choice == "1":
                    self.list_menu()
                elif choice == "2":
                    self.prize_menu()
                elif choice == "3":
                    self.start_lottery()
                elif choice == "4":
                    self.show_summary()
                elif choice == "5":
                    self.export_results()
                elif choice == "0":
                    self.out("Goodbye!")
                    return
                else:
                    self.out("Invalid choice.")
        except (EOFError, KeyboardInterrupt):
            self.out("\nExiting.")

    # ------------------------------------------------------------- lists
    def list_menu(self) -> None:
        while True:
            self.out("\nList Management:")
            self.out(" 1. Load built-in default list")
            self.out(" 2. Upload custom txt list (each line: Name,Department Group)")
            self.out(" 3. View group information")
            self.out(" 4. View all members")
            self.out(" 0. Back")
            choice = self.ask("Select: ")
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
                self._accept_list(users, errors)
            elif choice == "2":
                path = self.ask("Enter txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
                self._accept_list(users, errors)
            elif choice == "3":
                self.show_groups()
            elif choice == "4":
                if not self.users:
                    self.out("No list loaded.")
                for i, u in enumerate(self.users, 1):
                    self.out(f" {i}. {u.name} ({u.department})")
            elif choice == "0":
                return
            else:
                self.out("Invalid choice.")

    def _accept_list(self, users, errors) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            self.out("Problems detected in the list:")
            for e in errors:
                self.out("  " + e)
            for d in duplicates:
                self.out(f"  Duplicate name: {d.name} ({d.department})")
            if not users and errors:
                self.out("Upload terminated: no data loaded.")
                return
            while True:
                c = self.ask("Enter 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
                if c == "r":
                    break
                if c == "t":
                    self.out("Upload terminated.")
                    return
                self.out("Invalid input.")
        if not valid:
            self.out("No valid members in the list.")
            return
        if self.result_manager.winners:
            c = self.ask("Loading a new list clears existing results. Continue? (y/n): ").lower()
            if c != "y":
                self.out("Cancelled.")
                return
        self.users = valid
        self.lottery = None
        self.result_manager = ResultManager()
        self.completed = set()
        self.out(f"Loaded {len(valid)} valid members.")
        self.show_groups()

    def show_groups(self) -> None:
        if not self.users:
            self.out("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self.out("Valid groups:")
        for i, (dept, cnt) in enumerate(info.items(), 1):
            self.out(f" {i}. {dept}: {cnt} people")

    # ------------------------------------------------------------- prizes
    def prize_menu(self) -> None:
        while True:
            self.out("\nPrize Configuration:")
            self.out(" 1. Load preset prize library")
            self.out(" 2. Add custom prize")
            self.out(" 3. Set avoidance groups for a prize")
            self.out(" 4. View prizes (lottery order)")
            self.out(" 5. Reorder prizes")
            self.out(" 0. Back")
            choice = self.ask("Select: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                for e in errors:
                    self.out("  " + e)
                self.out("Preset prizes loaded.")
                self.show_prizes()
            elif choice == "2":
                self.add_custom_prize()
            elif choice == "3":
                self.set_avoid_groups()
            elif choice == "4":
                self.show_prizes()
            elif choice == "5":
                self.reorder()
            elif choice == "0":
                return
            else:
                self.out("Invalid choice.")

    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if not groups:
            raw = self.ask("No list loaded. Enter avoidance group names separated by commas (blank for none): ")
            return [g.strip() for g in raw.replace("\uff0c", ",").split(",") if g.strip()]
        self.out("Available groups:")
        for i, g in enumerate(groups, 1):
            self.out(f" {i}. {g}")
        while True:
            raw = self.ask("Select avoidance groups by number, comma separated (blank for none): ")
            if not raw:
                return []
            try:
                idxs = [int(x) for x in raw.replace("\uff0c", ",").split(",") if x.strip()]
            except ValueError:
                self.out("Invalid input.")
                continue
            if all(1 <= i <= len(groups) for i in idxs):
                result = []
                for i in idxs:
                    if groups[i - 1] not in result:
                        result.append(groups[i - 1])
                return result
            self.out("Number out of range.")

    def add_custom_prize(self) -> None:
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        drawer = self.ask("Associated lottery person (blank for none): ") or None
        groups = self._select_groups()
        try:
            prize = self.prize_manager.add_prize(name, qty, groups, drawer)
        except ValueError as exc:
            self.out(f"Error: {exc}")
            return
        self.out(f"Added: {prize}")

    def set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        self.show_prizes()
        raw = self.ask("Prize number: ")
        try:
            idx = int(raw) - 1
        except ValueError:
            self.out("Invalid input.")
            return
        if not 0 <= idx < len(prizes):
            self.out("Number out of range.")
            return
        groups = self._select_groups()
        self.prize_manager.set_avoid_groups(idx, groups)
        self.out(f"Updated: {self.prize_manager.get_prizes()[idx]}")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        self.out("Prizes (lottery order):")
        for i, p in enumerate(prizes, 1):
            status = " [drawn]" if p.name in self.completed else ""
            self.out(f" {i}. {p}{status}")

    def reorder(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            self.out("Need at least two prizes to reorder.")
            return
        self.show_prizes()
        raw = self.ask("Enter new order as current serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("\uff0c", ",").replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            self.out("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Prizes reordered.")
            self.show_prizes()
        else:
            self.out("Invalid order: must contain each serial number exactly once.")

    # ------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users:
            self.out("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        pending = [p for p in prizes if p.name not in self.completed]
        if not pending:
            self.out("All rounds have been completed.")
            return
        total = len(pending)
        for i, prize in enumerate(pending, 1):
            self._run_round(prize, i, total)
            self.completed.add(prize.name)
        self.out("\nAll rounds completed!")
        self.show_summary()

    def _run_round(self, prize, idx, total) -> None:
        self.out("\n" + "=" * 60)
        self.out(f"Round {idx}/{total}: {prize.name}")
        self.out(f"Quantity: {prize.quantity}")
        self.out(f"Lottery person: {prize.associated_drawer or 'Not specified'}")
        self.out(f"Rules: {self.lottery.describe_rules(prize)}")
        self.out("Commands: [Enter]=draw next, 'auto'=draw all remaining, 'pause', 'continue', 'terminate'")
        self.out("=" * 60)
        results: List[User] = []
        auto = False
        terminated = False
        while len(results) < prize.quantity and not terminated:
            if not auto:
                cmd = self.ask(f"[{prize.name}] command: ").lower()
                if cmd == "pause":
                    self.out("Lottery paused.")
                    while True:
                        c = self.ask("Paused. Type 'continue' to resume or 'terminate' to end this round: ").lower()
                        if c == "continue":
                            self.out("Lottery resumed.")
                            break
                        if c == "terminate":
                            terminated = True
                            break
                        self.out("Invalid command while paused.")
                    continue
                if cmd == "terminate":
                    terminated = True
                    continue
                if cmd == "continue":
                    self.out("Lottery is not paused.")
                    continue
                if cmd == "auto":
                    auto = True
                elif cmd not in ("", "draw"):
                    self.out("Invalid command.")
                    continue
            self.out(f"Currently drawing the {ordinal(len(results) + 1)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                self.out("No eligible participants left for this prize.")
                break
            results.append(user)
            self.out(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        if terminated:
            self.out(f"Round '{prize.name}' terminated; skipping to next round.")
        self.lottery.finish_round(prize, results)
        self.out(f"\nResults of round '{prize.name}':")
        if not results:
            self.out("  No winners.")
        for n, u in enumerate(results, 1):
            self.out(f"  {n}. {u.name} ({u.department})")

    # ------------------------------------------------------------- results
    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.winners:
            self.out("No winners yet.")
            return
        self.out("\n===== Complete Winner List =====")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self.out(f"{prize_name}:")
            for n, w in enumerate(winners, 1):
                self.out(f"  {n}. {w.user.name} ({w.user.department}) - {prize_name} - {w.time_str}")

    def export_results(self) -> None:
        if not self.result_manager.winners:
            self.out("No winners to export.")
            return
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.out(msg)


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
