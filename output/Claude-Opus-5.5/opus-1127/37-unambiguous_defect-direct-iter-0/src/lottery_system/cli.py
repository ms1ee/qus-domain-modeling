"""Command-line interface for the lottery system."""

from typing import List

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "q"


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: List[User] = []
        self.lottery = None

    # ---------- list ----------
    def _accept_list(self, users, errors) -> None:
        if errors:
            print("\nProblems detected:")
            for e in errors:
                print("  " + e)
            if not users:
                print("No valid data loaded.")
                return
            c = ask("Remove invalid data and continue (r) or terminate upload (t)? [r/t]: ").lower()
            if c != "r":
                print("Upload terminated.")
                return
        valid, dups = self.list_manager.validate_users(users)
        if dups:
            print("\nDuplicate names detected:")
            for d in dups:
                print(f"  {d.name} ({d.department})")
            c = ask("Remove duplicates and continue (r) or terminate upload (t)? [r/t]: ").lower()
            if c != "r":
                print("Upload terminated.")
                return
        self.users = valid
        self.lottery = None
        print(f"List loaded: {len(valid)} valid participants.")

    def menu_list(self):
        while True:
            print("\n--- List Management ---")
            print("1. Load default list\n2. Upload custom txt list (Name,Department per line)")
            print("3. View groups\n4. View participants\n0. Back")
            c = ask("Choice: ")
            if c == "1":
                self._accept_list(*self.list_manager.load_default_list())
            elif c == "2":
                path = ask("File path: ")
                self._accept_list(*self.list_manager.load_custom_list(path))
            elif c == "3":
                info = self.list_manager.get_group_info(self.users)
                if not info:
                    print("No list loaded.")
                for dept, cnt in info.items():
                    print(f"  {dept}: {cnt}")
            elif c == "4":
                for i, u in enumerate(self.users, 1):
                    print(f"  {i}. {u.name} ({u.department})")
                if not self.users:
                    print("No list loaded.")
            elif c in ("0", "q"):
                return

    # ---------- prizes ----------
    def _show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
        for i, p in enumerate(prizes, 1):
            print(f"  {i}. {p.name} x{p.quantity} | {p.rule_description()}")

    def _select_groups(self) -> List[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys())
        if groups:
            for i, g in enumerate(groups, 1):
                print(f"  {i}. {g}")
        raw = ask("Avoidance groups (numbers or names, comma-separated, empty for none): ")
        result = []
        for token in raw.replace("\uff0c", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(groups):
                result.append(groups[int(token) - 1])
            else:
                result.append(token)
        return result

    def menu_prizes(self):
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prizes\n2. Add custom prize\n3. View prizes")
            print("4. Reorder prizes\n0. Back")
            c = ask("Choice: ")
            if c == "1":
                for e in self.prize_manager.load_default_prizes():
                    print("  " + e)
                self._show_prizes()
            elif c == "2":
                name = ask("Prize name: ")
                qty = ask("Quantity: ")
                groups = self._select_groups()
                drawer = ask("Associated lottery person (empty for none): ") or None
                try:
                    self.prize_manager.add_prize(name, qty, groups, drawer)
                    print("Prize added.")
                except ValueError as exc:
                    print(f"Error: {exc}")
            elif c == "3":
                self._show_prizes()
            elif c == "4":
                self._show_prizes()
                raw = ask("New order (serial numbers separated by spaces/commas): ")
                tokens = raw.replace(",", " ").split()
                if self.prize_manager.reorder_prizes(tokens):
                    print("Prizes reordered.")
                    self._show_prizes()
                else:
                    print("Invalid order.")
            elif c in ("0", "q"):
                return

    # ---------- lottery ----------
    def run_lottery(self):
        if not self.users:
            print("Please load a list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
            for w in self.result_manager.winners:
                self.lottery.winner_names.add(w.user.name.lower())
        print("\nCommands during draw: [Enter]=draw next, pause, continue, terminate")
        for rnd, prize in enumerate(prizes, 1):
            print(f"\n===== Round {rnd}: {prize.name} (Quantity: {prize.quantity}) =====")
            print("Rules: " + prize.rule_description())
            if self.lottery.is_fallback_active(prize):
                print("Fallback active: prize pool limited to Cheng Ru group members.")
            round_winners = []
            terminated = False
            for i in range(1, prize.quantity + 1):
                cmd = ask(f"Ready to draw winner {i} > ").lower()
                while cmd == "pause":
                    print("Lottery paused. Type 'continue' to resume or 'terminate' to skip round.")
                    cmd = ask("(paused) > ").lower()
                    if cmd not in ("continue", "terminate"):
                        cmd = "pause"
                if cmd in ("terminate", "q"):
                    print("Current round terminated.")
                    terminated = True
                    break
                print(f"Currently drawing the {i}th winner...")
                user = self.lottery.draw_one(prize)
                if user is None:
                    print("No eligible participants remain for this prize.")
                    break
                self.result_manager.add_winner(user, prize)
                round_winners.append(user)
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
            self.lottery.record_round(prize, round_winners)
            print(f"--- Round {rnd} results ---")
            for idx, u in enumerate(round_winners, 1):
                print(f"  {idx}. {u.name} ({u.department}) - {prize.name}")
            if not round_winners:
                print("  No winners." + (" (terminated)" if terminated else ""))
        self.show_summary()

    def show_summary(self):
        print("\n===== Complete Winner List =====")
        grouped = self.result_manager.get_winners_by_prize(self.prize_manager.get_prizes())
        any_w = False
        for name, winners in grouped.items():
            if not winners:
                continue
            any_w = True
            print(f"[{name}]")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {name}")
        if not any_w:
            print("No winners yet.")

    def run(self):
        print("=== Company Team Building Smart Lottery System ===")
        while True:
            print("\n1. List management\n2. Prize configuration\n3. Start lottery")
            print("4. Show results\n5. Export results\n0. Exit")
            c = ask("Choice: ")
            if c == "1":
                self.menu_list()
            elif c == "2":
                self.menu_prizes()
            elif c == "3":
                self.run_lottery()
            elif c == "4":
                self.show_summary()
            elif c == "5":
                ok, msg = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
                print(msg)
            elif c in ("0", "q"):
                print("Goodbye.")
                return


def main():
    LotteryCLI().run()


if __name__ == "__main__":
    main()
