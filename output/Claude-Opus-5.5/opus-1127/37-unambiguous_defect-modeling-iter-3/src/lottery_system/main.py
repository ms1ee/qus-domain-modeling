"""Command-line interface of the lottery system."""
from __future__ import annotations

from typing import List, Optional

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


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery_manager: Optional[LotteryManager] = None
        self.drawn_prizes = set()

    @staticmethod
    def ask(prompt: str) -> str:
        try:
            return input(prompt).strip()
        except EOFError:
            return "0"

    # ------------------------------------------------------------ list module
    def _set_users(self, users: List[User]) -> None:
        self.users = users
        self.lottery_manager = None
        self.result_manager = ResultManager()
        self.drawn_prizes = set()
        print(f"{len(users)} valid participants loaded.")

    def _handle_loaded(self, users, errors) -> None:
        if errors:
            print("The following problems were detected:")
            for e in errors:
                print("  " + e)
            if not users:
                print("No valid data. Upload terminated.")
                return
            c = self.ask("Remove invalid data and continue (r) or terminate upload (t)? ").lower()
            if c != "r":
                print("Upload terminated.")
                return
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  Duplicate Name: {d.name} ({d.department})")
            c = self.ask("Remove duplicates and continue (r) or terminate upload (t)? ").lower()
            if c != "r":
                print("Upload terminated.")
                return
        self._set_users(valid)

    def list_menu(self) -> None:
        while True:
            print("\n--- List Management ---")
            print("1. Load built-in default list")
            print("2. Upload custom txt list (format per line: Name,Department)")
            print("3. View groups")
            print("4. View participants")
            print("0. Back")
            c = self.ask("Choice: ")
            if c == "1":
                self._handle_loaded(*self.list_manager.load_default_list())
            elif c == "2":
                path = self.ask("txt file path: ")
                self._handle_loaded(*self.list_manager.load_custom_list(path))
            elif c == "3":
                info = self.list_manager.get_group_info(self.users)
                if not info:
                    print("No list loaded.")
                for i, (g, n) in enumerate(info.items(), 1):
                    print(f"  {i}. {g}: {n} people")
            elif c == "4":
                if not self.users:
                    print("No list loaded.")
                for u in self.users:
                    print(f"  {u.name} ({u.department})")
            elif c == "0":
                return
            else:
                print("Invalid choice.")

    # ----------------------------------------------------------- prize module
    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            raw = self.ask("Avoidance groups (numbers or names, comma separated, empty for none): ")
        else:
            raw = self.ask("Avoidance group names (comma separated, empty for none): ")
        result = []
        for token in raw.replace("，", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                name = groups[int(token) - 1]
            else:
                name = token
            if name not in result:
                result.append(name)
        return result

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            mark = " [drawn]" if p.name in self.drawn_prizes else ""
            print(f"  {i}. {p.describe()}{mark}")

    def prize_menu(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. View prizes (round order)")
            print("4. Reorder prizes")
            print("0. Back")
            c = self.ask("Choice: ")
            if c == "1":
                errors = self.prize_manager.load_default_prizes()
                for e in errors:
                    print("  " + e)
                self.show_prizes()
            elif c == "2":
                name = self.ask("Prize name: ")
                qty = self.ask("Quantity: ")
                avoid = self._select_groups()
                drawer = self.ask("Associated lottery person (empty for none): ") or None
                try:
                    self.prize_manager.add_prize(name, qty, avoid, drawer)
                    print("Prize added.")
                except ValueError as exc:
                    print(f"Error: {exc}")
            elif c == "3":
                self.show_prizes()
            elif c == "4":
                self.show_prizes()
                raw = self.ask("New order as serial numbers (e.g. 3,1,2): ")
                try:
                    order = [int(x) for x in raw.replace(" ", ",").split(",") if x.strip()]
                except ValueError:
                    order = []
                if self.prize_manager.reorder_prizes(order):
                    print("Prizes reordered.")
                    self.show_prizes()
                else:
                    print("Invalid order.")
            elif c == "0":
                return
            else:
                print("Invalid choice.")

    # --------------------------------------------------------------- lottery
    def run_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = [p for p in self.prize_manager.get_prizes() if p.name not in self.drawn_prizes]
        if not prizes:
            print("No prizes left to draw. Please configure prizes.")
            return
        if self.lottery_manager is None:
            self.lottery_manager = LotteryManager(self.users)
        lm = self.lottery_manager
        auto = False
        for idx, prize in enumerate(prizes, 1):
            print("\n" + "=" * 60)
            print(f"Round {idx}: {prize.name}")
            print(f"Quantity: {prize.quantity}")
            print(f"Rules: {lm.get_rule_description(prize)}")
            print("=" * 60)
            round_winners: List[User] = []
            while len(round_winners) < prize.quantity:
                n = len(round_winners) + 1
                if not auto:
                    cmd = self.ask(f"Enter to draw the {ordinal(n)} winner "
                                   "(commands: pause / terminate / auto): ").lower()
                    if cmd == "pause":
                        print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                        stop = False
                        while True:
                            c = self.ask("> ").lower()
                            if c == "continue":
                                print("Lottery resumed.")
                                break
                            if c in ("terminate", "0"):
                                stop = True
                                break
                            print("Paused. Type 'continue' or 'terminate'.")
                        if stop:
                            print("Current round terminated.")
                            break
                        continue
                    if cmd in ("terminate", "0"):
                        print("Current round terminated.")
                        break
                    if cmd == "auto":
                        auto = True
                    elif cmd not in ("", "draw", "continue"):
                        print("Unknown command.")
                        continue
                print(f"Currently drawing the {ordinal(n)} winner...")
                user = lm.draw_winner(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            lm.finish_round(prize, round_winners)
            self.drawn_prizes.add(prize.name)
            print(f"\nRound {idx} results - {prize.name}:")
            if not round_winners:
                print("  No winners.")
            for i, u in enumerate(round_winners, 1):
                print(f"  {i}. {u.name} ({u.department})")
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("\n===== Complete Winner List =====")
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        for prize_name, ws in grouped.items():
            if not ws:
                continue
            print(f"[{prize_name}]")
            for w in ws:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} "
                      f"@ {w.win_time.strftime('%H:%M:%S')}")

    # ------------------------------------------------------------------ main
    def run(self) -> None:
        print("Welcome to the Team Building Smart Lottery System")
        while True:
            print("\n===== Main Menu =====")
            print("1. List management")
            print("2. Prize configuration")
            print("3. Start lottery")
            print("4. View winner summary")
            print("5. Export results")
            print("0. Exit")
            c = self.ask("Choice: ")
            if c == "1":
                self.list_menu()
            elif c == "2":
                self.prize_menu()
            elif c == "3":
                self.run_lottery()
            elif c == "4":
                self.show_summary()
            elif c == "5":
                ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
                print(msg)
            elif c == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid choice.")


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
