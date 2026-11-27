"""Command-line interface for the lottery system."""

from __future__ import annotations

from typing import List, Optional

from lottery_system.models import User, normalize_name
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class LotteryApp:
    def __init__(self) -> None:
        self.event_name = "Company Team Building Event"
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery: Optional[LotteryManager] = None
        self.drawn_prizes = set()

    # ---------------------------------------------------------------- utils
    @staticmethod
    def ask(prompt: str) -> str:
        try:
            return input(prompt)
        except EOFError:
            return "0"

    def _set_users(self, users: List[User]) -> None:
        self.users = users
        self.lottery = None

    def _get_lottery(self) -> LotteryManager:
        if self.lottery is None:
            self.lottery = LotteryManager(self.users, self.result_manager)
        return self.lottery

    def _handle_loaded(self, users, errors) -> None:
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
            print("No valid participants loaded.")
            return
        if errors or dups:
            choice = self.ask(
                "1. Remove invalid data and continue  2. Terminate upload\nChoose: "
            ).strip()
            if choice != "1":
                print("Upload terminated. Current list unchanged.")
                return
        self._set_users(valid)
        print(f"Loaded {len(valid)} valid participants.")

    # ---------------------------------------------------------------- actions
    def load_default(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._handle_loaded(users, errors)

    def load_custom(self) -> None:
        path = self.ask("Enter txt file path (each line 'Name,Department Group'): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        if not users and errors:
            for e in errors:
                print(e)
            return
        self._handle_loaded(users, errors)

    def view_groups(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Valid groups ({len(info)}):")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    def remove_participant(self) -> None:
        if not self.users:
            print("No list loaded.")
            return
        name = self.ask("Enter name to remove: ").strip()
        before = len(self.users)
        self._set_users([u for u in self.users if normalize_name(u.name) != normalize_name(name)])
        print("Removed." if len(self.users) < before else "Name not found.")

    def view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            avoid = ", ".join(p.avoid_groups) if p.avoid_groups else "None"
            drawer = p.associated_drawer or "None"
            status = " [drawn]" if p.name in self.drawn_prizes else ""
            print(f"  {i}. {p.name} | Qty: {p.quantity} | Avoid: {avoid} | Drawer: {drawer}{status}")

    def add_prize(self) -> None:
        name = self.ask("Prize name: ").strip()
        qty = self.ask("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid: List[str] = []
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
            sel = self.ask("Avoidance groups (numbers separated by comma, blank for none): ").strip()
            for part in sel.replace("，", ",").split(","):
                part = part.strip()
                if part.isdigit() and 1 <= int(part) <= len(groups):
                    if groups[int(part) - 1] not in avoid:
                        avoid.append(groups[int(part) - 1])
                elif part:
                    print(f"Ignored invalid selection '{part}'")
        else:
            sel = self.ask("Avoidance groups (names separated by comma, blank for none): ")
            avoid = [g.strip() for g in sel.split(",") if g.strip()]
        drawer = self.ask("Associated lottery person (blank for none): ").strip() or None
        try:
            p = self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{p.name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def reorder(self) -> None:
        self.view_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = self.ask("Enter new order of serial numbers (e.g. 3,1,2): ")
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x.strip()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prizes reordered.")
            self.view_prizes()
        else:
            print("Invalid order: must contain each serial number exactly once.")

    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        lottery = self._get_lottery()
        for rnd, prize in enumerate(prizes, 1):
            if prize.name in self.drawn_prizes:
                print(f"Round {rnd}: {prize.name} already drawn, skipped.")
                continue
            print("=" * 60)
            print(f"Round {rnd}: {prize.name}")
            print(f"Quantity: {prize.quantity}")
            print(f"Rules: {lottery.describe_rules(prize)}")
            print("=" * 60)
            winners = lottery.run_round(prize, rnd, self.ask, print, True)
            self.drawn_prizes.add(prize.name)
            print(f"--- Round {rnd} results ({prize.name}) ---")
            if not winners:
                print("  No winners in this round.")
            for i, w in enumerate(winners, 1):
                print(f"  {i}. {w.user.name} ({w.user.department}) - {w.prize_name}")
        print("All rounds completed.")
        self.show_summary()

    def show_summary(self) -> None:
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        print("=" * 60)
        print("Complete Winner List")
        if not self.result_manager.winners:
            print("  No winners yet.")
            return
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"[{prize_name}]")
            for w in winners:
                print(
                    f"  {w.user.name} ({w.user.department}) - {w.prize_name} "
                    f"@ {w.win_time.strftime('%H:%M:%S')}"
                )

    def export(self) -> None:
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ---------------------------------------------------------------- loop
    def run(self) -> None:
        print(f"=== {self.event_name} Smart Lottery System ===")
        actions = {
            "1": self.load_default,
            "2": self.load_custom,
            "3": self.view_groups,
            "4": self.remove_participant,
            "5": lambda: [print(e) for e in self.prize_manager.load_default_prizes()]
            or print("Preset prizes loaded."),
            "6": self.add_prize,
            "7": self.view_prizes,
            "8": self.reorder,
            "9": self.start_lottery,
            "10": self.show_summary,
            "11": self.export,
        }
        while True:
            print(
                "\n1. Load default list   2. Upload custom list   3. View groups\n"
                "4. Remove participant  5. Load preset prizes   6. Add custom prize\n"
                "7. View prizes         8. Reorder prizes       9. Start lottery\n"
                "10. View results       11. Export results      0. Exit"
            )
            choice = self.ask("Choose: ").strip()
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid choice.")
                continue
            action()


def main() -> None:
    LotteryApp().run()


if __name__ == "__main__":
    main()
