"""Command-line interface of the lottery system."""

from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class _Exit(Exception):
    pass


def _input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        raise _Exit()


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = LotteryManager([], self.result_manager)
        self.status = "idle"
        self.current_round_index = 0

    # ----------------------------------------------------------- list
    def _set_users(self, users):
        self.users = users
        self.result_manager = ResultManager()
        self.lottery = LotteryManager(users, self.result_manager)
        print(f"{len(users)} valid participants loaded.")

    def _confirm_remove(self) -> bool:
        while True:
            c = _input("Type 'r' to remove invalid data and continue, 't' to terminate upload: ").strip().lower()
            if c in ("r", "remove"):
                return True
            if c in ("t", "terminate"):
                return False

    def _process_loaded(self, users, errors):
        if errors:
            print("Problems found:")
            for e in errors:
                print("  " + e)
            if not users or not self._confirm_remove():
                print("Upload terminated.")
                return
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("Duplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
            if not self._confirm_remove():
                print("Upload terminated.")
                return
        if not valid:
            print("No valid participants.")
            return
        self._set_users(valid)

    def load_default(self):
        users, errors = self.list_manager.load_default_list()
        self._process_loaded(users, errors)

    def load_custom(self):
        path = _input("Enter txt list path (each line 'Name,Department Group'): ").strip()
        users, errors = self.list_manager.load_custom_list(path)
        self._process_loaded(users, errors)

    def show_groups(self):
        info = self.list_manager.get_group_info(self.users)
        if not info:
            print("No list loaded.")
            return
        print("Current valid groups:")
        for i, (g, c) in enumerate(info.items(), 1):
            print(f"  {i}. {g}: {c} people")

    # --------------------------------------------------------- prizes
    def load_preset_prizes(self):
        errors = self.prize_manager.load_default_prizes()
        for e in errors:
            print("  " + e)
        print("Preset prize library loaded.")

    def add_custom_prize(self):
        name = _input("Prize name: ").strip()
        qty = _input("Quantity: ").strip()
        groups = list(self.list_manager.get_group_info(self.users).keys())
        avoid = []
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = _input("Avoidance groups (numbers or names, comma separated, empty for none): ").strip()
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and 1 <= int(part) <= len(groups):
                avoid.append(groups[int(part) - 1])
            else:
                avoid.append(part)
        drawer = _input("Associated lottery person (empty for none): ").strip() or None
        try:
            self.prize_manager.add_prize(name, qty, avoid, drawer)
            print(f"Prize '{name}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def reorder(self):
        self.show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = _input("Enter new order of serial numbers (e.g. 3,1,2): ").strip()
        try:
            order = [int(x) for x in raw.replace("，", ",").replace(" ", ",").split(",") if x]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
            self.show_prizes()
        else:
            print("Invalid order; it must be a permutation of the current serial numbers.")

    # -------------------------------------------------------- lottery
    def run_lottery(self):
        prizes = self.prize_manager.get_prizes()
        if not self.users:
            print("Please load a participant list first.")
            return
        if not prizes:
            print("Please configure prizes first.")
            return
        self.status = "running"
        for idx, prize in enumerate(prizes, 1):
            self.current_round_index = idx
            print("\n" + "=" * 60)
            print(f"Round {idx}: {prize.name} | Quantity: {prize.quantity}")
            print(f"Rules: {self.lottery.describe_rules(prize)}")
            print("Commands: [Enter]=draw next, pause, continue, terminate")
            round_winners = []
            terminated = False
            paused = False
            while len(round_winners) < prize.quantity:
                cmd = _input("> ").strip().lower()
                if cmd == "pause":
                    paused = True
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
                    continue
                if cmd == "terminate":
                    terminated = True
                    print("Current round terminated.")
                    break
                if cmd == "continue":
                    if paused:
                        paused = False
                        print("Lottery resumed.")
                    continue
                if paused:
                    print("Lottery is paused. Type 'continue' or 'terminate'.")
                    continue
                print(f"Currently drawing the {_ordinal(len(round_winners) + 1)} winner...")
                user = self.lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.complete_round(prize, round_winners)
            print(f"--- Round {idx} results ({prize.name}){' [terminated]' if terminated else ''} ---")
            if not round_winners:
                print("  (no winners)")
            for i, u in enumerate(round_winners, 1):
                print(f"  {i}. {u.name} ({u.department})")
        self.status = "finished"
        print("\nAll rounds completed.")
        self.show_summary()

    def show_summary(self):
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        if not self.result_manager.winners:
            print("No winners yet.")
            return
        print("\n===== Complete Winner List =====")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            print(f"[{prize_name}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {prize_name} "
                      f"@ {w.winning_time.strftime('%H:%M:%S')}")

    def export(self):
        ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(msg)

    # ----------------------------------------------------------- main
    def run(self):
        menu = {
            "1": ("Load default team building list", self.load_default),
            "2": ("Upload custom txt list", self.load_custom),
            "3": ("View groups", self.show_groups),
            "4": ("Load preset prize library", self.load_preset_prizes),
            "5": ("Add custom prize", self.add_custom_prize),
            "6": ("View prizes", self.show_prizes),
            "7": ("Reorder prizes", self.reorder),
            "8": ("Start lottery", self.run_lottery),
            "9": ("View winner summary", self.show_summary),
            "10": ("Export results", self.export),
        }
        try:
            while True:
                print("\n===== Team Building Smart Lottery System =====")
                for k, (label, _) in menu.items():
                    print(f"{k}. {label}")
                print("0. Exit")
                choice = _input("Select: ").strip()
                if choice == "0":
                    break
                if choice in menu:
                    menu[choice][1]()
                else:
                    print("Invalid choice.")
        except (_Exit, KeyboardInterrupt):
            print()
        print("Goodbye!")


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
