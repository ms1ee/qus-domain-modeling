"""Command-line interface of the lottery system."""

from __future__ import annotations

from typing import List, Optional, Set

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class _Exit(Exception):
    pass


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
        raise _Exit()


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery: Optional[LotteryManager] = None
        self.completed: Set[str] = set()

    # ------------------------------------------------------------------- lists
    def _accept_list(self, users: List[User], errors: List[str]) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if errors:
            print("Format errors detected:")
            for e in errors:
                print("  " + e)
        if duplicates:
            print("Duplicate names detected:")
            for d in duplicates:
                print(f"  {d.name} ({d.department})")
        if errors or duplicates:
            choice = ask("Input 'r' to remove invalid data and continue, 't' to terminate upload: ").strip().lower()
            if choice != "r":
                print("Upload terminated. Current list unchanged.")
                return
        while True:
            name = ask("Input a name to remove manually (Enter to finish): ").strip()
            if not name:
                break
            before = len(valid)
            valid = self.list_manager.remove_user(valid, name)
            print("Removed." if len(valid) < before else "Name not found.")
        if not valid:
            print("No valid participants loaded.")
            return
        self.users = valid
        self.lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        self.completed = set()
        print(f"Loaded {len(valid)} valid participants.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors)

    def load_custom(self) -> None:
        path = ask("Input txt file path (one 'Name,Department' per line): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print("  " + e)
            print("No participants loaded.")
            return
        self._accept_list(users, errors)

    def view_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current valid groups:")
        for i, (dept, cnt) in enumerate(info.items(), 1):
            print(f"  {i}. {dept}: {cnt} people")

    # ------------------------------------------------------------------ prizes
    def load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prizes loaded.")

    def add_custom_prize(self) -> None:
        name = ask("Prize name: ").strip()
        qty = ask("Quantity: ").strip()
        avoid: List[str] = []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = ask("Avoidance groups (serial numbers separated by spaces/commas, Enter for none): ")
            for token in sel.replace(",", " ").split():
                if token.isdigit() and 1 <= int(token) <= len(groups):
                    if groups[int(token) - 1] not in avoid:
                        avoid.append(groups[int(token) - 1])
                else:
                    print(f"  Ignored invalid selection: {token}")
        else:
            sel = ask("Avoidance groups (names separated by commas, Enter for none): ")
            avoid = [s.strip() for s in sel.split(",") if s.strip()]
        drawer = ask("Associated lottery person (Enter for none): ").strip() or None
        try:
            prize = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Added: {prize}")
        except ValueError as exc:
            print(f"Error: {exc}")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            status = " [done]" if p.name in self.completed else ""
            print(f"  {i}. {p}{status}")

    def reorder(self) -> None:
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        text = ask("Input new order of serial numbers (e.g. 3 1 2): ")
        order = text.replace(",", " ").split()
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.view_prizes()
        else:
            print("Invalid order. Must be a permutation of all serial numbers.")

    # ----------------------------------------------------------------- lottery
    def _control(self) -> str:
        """Return 'draw' or 'terminate'."""
        while True:
            cmd = ask("[Enter]=draw | pause | terminate > ").strip().lower()
            if cmd in ("", "draw", "continue"):
                return "draw"
            if cmd == "terminate":
                return "terminate"
            if cmd == "pause":
                print("Lottery paused. Input 'continue' to resume or 'terminate' to end this round.")
                while True:
                    c = ask("(paused) > ").strip().lower()
                    if c == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if c == "terminate":
                        return "terminate"
                    print("Lottery is paused. Input 'continue' or 'terminate'.")
            print("Unknown command.")

    def run_lottery(self) -> None:
        if not self.users or self.lottery is None:
            print("Please load a participant list first.")
            return
        prizes = [p for p in self.prize_manager.get_prizes() if p.name not in self.completed]
        if not prizes:
            print("No pending prizes to draw.")
            return
        for round_no, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {round_no}: {prize.name}")
            print(f"Quantity: {prize.quantity}")
            print(f"Rules: {self.lottery.get_rule_description(prize)}")
            print("=" * 60)
            round_winners: List[User] = []
            for i in range(1, prize.quantity + 1):
                if self._control() == "terminate":
                    print("Current round terminated, skipping.")
                    break
                print(f"Currently drawing the {ordinal(i)} winner...")
                winner = self.lottery.draw_one(prize)
                if winner is None:
                    print("No eligible participants left for this prize.")
                    break
                self.result_manager.add_winner(winner, prize)
                round_winners.append(winner)
                print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")
            self.lottery.record_round_result(prize, round_winners)
            self.completed.add(prize.name)
            print(f"\nRound {round_no} results ({prize.name}):")
            if round_winners:
                for i, w in enumerate(round_winners, 1):
                    print(f"  {i}. {w.name} ({w.department})")
            else:
                print("  No winners.")
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"{prize_name}:")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} "
                      f"[{w.win_time:%H:%M:%S}]")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # -------------------------------------------------------------------- menu
    def run(self) -> None:
        actions = {
            "1": ("Load default team building list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups and member counts", self.view_groups),
            "4": ("Load preset prize library", self.load_preset_prizes),
            "5": ("Add custom prize", self.add_custom_prize),
            "6": ("View prizes", self.view_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.run_lottery),
            "9": ("View winner summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        try:
            while True:
                print("\n===== Team Building Smart Lottery System =====")
                for key, (label, _) in actions.items():
                    print(f"{key}. {label}")
                print("0. Exit")
                choice = ask("Select: ").strip()
                if choice == "0":
                    break
                if choice in actions:
                    actions[choice][1]()
                else:
                    print("Invalid selection.")
        except (_Exit, KeyboardInterrupt):
            print()
        print("Goodbye.")


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
