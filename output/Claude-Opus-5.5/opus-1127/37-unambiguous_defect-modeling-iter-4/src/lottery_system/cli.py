"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import Callable, List

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

MENU = """
========== Team Building Smart Lottery ==========
 1. Load default participant list
 2. Upload custom participant list (txt, 'Name,Department' per line)
 3. View groups
 4. Load preset prize library
 5. Add custom prize
 6. View prizes
 7. Reorder prizes
 8. Start lottery
 9. View result summary
10. Export results
 0. Exit
================================================="""


class LotteryApp:
    def __init__(self, input_func: Callable[[str], str] = input,
                 output_func: Callable[[str], None] = print):
        self.inp = input_func
        self.out = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager: LotteryManager | None = None
        self.drawn_prizes = set()

    def ask(self, prompt: str) -> str:
        return self.inp(prompt).strip()

    # ------------------------------------------------------------------ lists
    def _set_users(self, users: List[User]) -> None:
        if self.result_manager.get_winners():
            self.out("Note: a new list was loaded; previous lottery results are cleared.")
        self.users = users
        self.result_manager.clear()
        self.drawn_prizes.clear()
        self.lottery_manager = LotteryManager(users, self.result_manager)
        self.out(f"{len(users)} valid participants loaded.")

    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        for e in errors:
            self.out(e)
        valid, dups = self.list_manager.validate_users(users)
        self._set_users(valid)

    def load_custom(self) -> None:
        path = self.ask("Enter txt file path: ")
        users, errors = self.list_manager.load_custom_list(path)
        valid, dups = self.list_manager.validate_users(users)
        if errors or dups:
            self.out("Validation issues detected:")
            for e in errors:
                self.out("  " + e)
            for d in dups:
                self.out(f"  Duplicate Name: {d.name} ({d.department})")
            if not valid:
                self.out("No valid data. Upload terminated.")
                return
            choice = self.ask("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").lower()
            if choice != "r":
                self.out("Upload terminated.")
                return
        if not valid:
            self.out("No valid participants found.")
            return
        self._set_users(valid)

    def view_groups(self) -> List[str]:
        info = self.list_manager.get_group_info(self.users)
        if not info:
            self.out("No participants loaded.")
            return []
        self.out("Current groups:")
        names = list(info.keys())
        for i, name in enumerate(names, start=1):
            self.out(f"  {i}. {name}: {info[name]} people")
        return names

    # ----------------------------------------------------------------- prizes
    def load_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            self.out(e)
        self.out("Preset prize library loaded.")

    def add_prize(self) -> None:
        name = self.ask("Prize name: ")
        qty = self.ask("Quantity: ")
        groups = self.view_groups()
        avoid: List[str] = []
        raw = self.ask("Avoidance groups (numbers or names, comma separated, blank for none): ")
        if raw:
            for tok in raw.replace("，", ",").split(","):
                tok = tok.strip()
                if not tok:
                    continue
                if tok.isdigit() and 1 <= int(tok) <= len(groups):
                    avoid.append(groups[int(tok) - 1])
                else:
                    avoid.append(tok)
        drawer = self.ask("Associated lottery person (blank for none): ") or None
        try:
            prize = self.prize_manager.add_prize(name, qty, avoid, drawer)
            self.out(f"Prize added: {prize}")
        except ValueError as exc:
            self.out(f"Error: {exc}")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self.out("No prizes configured.")
            return
        for i, p in enumerate(prizes, start=1):
            mark = " [drawn]" if p.name in self.drawn_prizes else ""
            self.out(f"  {i}. {p}{mark}")

    def reorder(self) -> None:
        self.view_prizes()
        raw = self.ask("Enter new order as serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            self.out("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            self.out("Prize order updated.")
            self.view_prizes()
        else:
            self.out("Invalid order: must be a permutation of all serial numbers.")

    # ---------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users or self.lottery_manager is None:
            self.out("Please load a participant list first.")
            return
        prizes = [p for p in self.prize_manager.get_prizes() if p.name not in self.drawn_prizes]
        if not prizes:
            self.out("No prizes left to draw. Please configure prizes.")
            return
        for prize in prizes:
            self.lottery_manager.run_round(prize, self.inp, self.out)
            self.drawn_prizes.add(prize.name)
        self.out("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.get_winners():
            self.out("No winners yet.")
            return
        self.out("\n========== Complete Winner List ==========")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self.out(f"[{prize_name}]")
            for w in winners:
                self.out(f"  {w.user.name} ({w.user.department}) - {prize_name} "
                         f"@ {w.win_time.strftime('%H:%M:%S')}")

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self.out(msg)

    # ------------------------------------------------------------------- loop
    def run(self) -> None:
        actions = {
            "1": self.load_default, "2": self.load_custom, "3": self.view_groups,
            "4": self.load_prizes, "5": self.add_prize, "6": self.view_prizes,
            "7": self.reorder, "8": self.start_lottery, "9": self.show_summary,
            "10": self.export,
        }
        while True:
            self.out(MENU)
            try:
                choice = self.ask("Select: ")
            except (EOFError, KeyboardInterrupt):
                self.out("\nBye.")
                return
            if choice == "0":
                self.out("Bye.")
                return
            action = actions.get(choice)
            if action is None:
                self.out("Invalid option.")
                continue
            try:
                action()
            except (EOFError, KeyboardInterrupt):
                self.out("\nBye.")
                return


def main() -> None:
    LotteryApp().run()


if __name__ == "__main__":
    main()
