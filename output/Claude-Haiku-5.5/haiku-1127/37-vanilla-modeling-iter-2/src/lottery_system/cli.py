"""Command-line interface for the lottery process."""

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import Winner

MENU = """
==========================================
 Team Building Smart Lottery System
==========================================
 1. Load participant list
 2. View department groups
 3. Prize configuration
 4. Adjust prize order
 5. Start lottery
 6. View winners / export results
 0. Exit
"""


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.last_prizes: list = []

    # ---------- helpers ----------
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt)

    def _group_map(self) -> dict[str, str]:
        groups = self.list_manager.get_group_info(self.users)
        return {name.casefold(): name for name in groups}

    # ---------- main loop ----------
    def run(self) -> None:
        print("Default prizes are not loaded automatically. Use menu 3 to load them.")
        while True:
            print(MENU)
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._load_list()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._start_lottery()
            elif choice == "6":
                self._winners_menu()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ---------- list management ----------
    def _load_list(self) -> None:
        print("1. Built-in default team building list")
        print("2. Custom txt file (each line: Name,Department Group)")
        choice = self._ask("Select source (1/2): ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid choice. List not changed.")
            return

        valid, duplicates = self.list_manager.validate_users(users)
        issues = list(errors) + [
            f"Duplicate name: '{u.name}' ({u.department})" for u in duplicates
        ]
        if issues:
            print("Verification found the following problems:")
            for issue in issues:
                print(f"  - {issue}")
            print(f"Valid entries: {len(valid)}")
            answer = self._ask(
                "Type 'remove' to discard invalid/duplicate data and continue, "
                "or 'terminate' to cancel the upload: "
            ).strip().lower()
            if answer != "remove":
                print("Upload terminated. Previous list kept.")
                return

        if not valid:
            print("No valid participants found. List not changed.")
            return
        self.users = valid
        print(f"Loaded {len(valid)} participants.")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in info.items():
            print(f"  - {group}: {count} people")
        print(f"Total: {len(self.users)} people")

    # ---------- prize configuration ----------
    def _prize_menu(self) -> None:
        while True:
            print("\n--- Prize configuration ---")
            print("1. View prizes")
            print("2. Load preset prizes")
            print("3. Add custom prize")
            print("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self._show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for err in errors:
                        print(f"  Failed: {err}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "3":
                self._add_prize()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for idx, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {idx}. {prize.name} | quantity: {prize.quantity} | "
                  f"avoid groups: {groups} | lottery person: {drawer}")

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        qty_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(qty_text)
        except ValueError:
            print("Quantity must be an integer.")
            return

        avoid: list[str] = []
        groups_text = self._ask(
            "Avoidance groups (comma-separated group names, empty for none): "
        ).strip()
        if groups_text:
            known = self._group_map()
            if not known:
                print("No participant list loaded; avoidance groups ignored.")
            for raw in groups_text.split(","):
                key = raw.strip().casefold()
                if not key:
                    continue
                if key in known:
                    avoid.append(known[key])
                else:
                    print(f"Warning: unknown group '{raw.strip()}' ignored.")

        drawer = self._ask("Associated lottery person (empty for none): ").strip() or None
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid, drawer)
            print(f"Prize added: {prize.name} (quantity {prize.quantity})")
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")

    # ---------- ordering ----------
    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (empty to keep): "
        ).strip()
        if not text:
            print("Order unchanged.")
            return
        try:
            order = [int(x) for x in text.replace(",", " ").split()]
        except ValueError:
            print("Serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated:")
            self._show_prizes()
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ---------- lottery process ----------
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        self.last_prizes = prizes
        print("\nLottery started!")
        for round_no, prize in enumerate(prizes, start=1):
            print(f"\n--- Round {round_no}/{len(prizes)} ---")
            self._run_round(lottery, round_no, prize)
        self.lottery = lottery

        print("\nAll rounds completed.")
        self._print_summary(lottery, prizes)
        if self._ask("Export results to txt now? (y/n): ").strip().lower() == "y":
            self._export(lottery, prizes)

    def _run_round(self, lottery: LotteryManager, round_no: int, prize) -> None:
        print(f"Prize: {prize.name} | Quantity: {prize.quantity}")
        print(f"Rule: {lottery.describe_rule(prize)}")
        drawn: list = []
        while len(drawn) < prize.quantity:
            target = ordinal(len(drawn) + 1)
            cmd = self._ask(
                f"Press Enter to draw the {target} winner "
                f"(commands: pause / terminate): "
            ).strip().lower()
            if cmd == "pause":
                cmd = self._wait_while_paused()
            if cmd == "terminate":
                print("Round terminated. Skipping remaining winners of this prize.")
                break
            if cmd not in ("", "continue"):
                print(f"Unknown command '{cmd}'.")
                continue

            print(f"Currently drawing the {target} winner...")
            user = lottery.draw(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            drawn.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"Round {round_no} results ({prize.name}):")
        if not drawn:
            print("  (no winners)")
        for idx, user in enumerate(drawn, start=1):
            print(f"  {idx}. {user.name} ({user.department})")

    def _wait_while_paused(self) -> str:
        print("Lottery paused.")
        while True:
            cmd = self._ask(
                "Type 'continue' to resume or 'terminate' to skip this round: "
            ).strip().lower()
            if cmd == "continue":
                print("Lottery resumed.")
                return "continue"
            if cmd == "terminate":
                return "terminate"
            print("Please type 'continue' or 'terminate'.")

    # ---------- results ----------
    def _print_summary(self, lottery: LotteryManager, prizes: list) -> None:
        grouped = lottery.result_manager.get_winners_by_prize(prizes)
        print("\n========== Winner List ==========")
        for prize_name, winners in grouped.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for idx, w in enumerate(winners, start=1):
                self._print_winner_line(idx, w)
        print("=================================")

    @staticmethod
    def _print_winner_line(idx: int, winner: Winner) -> None:
        print(f"  {idx}. {winner.user.name} ({winner.user.department}) "
              f"- {winner.winning_time:%H:%M:%S}")

    def _export(self, lottery: LotteryManager, prizes: list) -> None:
        ok, message = lottery.result_manager.export_to_csv(prizes)
        print(message)

    def _winners_menu(self) -> None:
        if self.lottery is None:
            print("No lottery results yet.")
            return
        self._print_summary(self.lottery, self.last_prizes)
        if self._ask("Export results to txt? (y/n): ").strip().lower() == "y":
            self._export(self.lottery, self.last_prizes)


def main() -> None:
    try:
        LotteryCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
