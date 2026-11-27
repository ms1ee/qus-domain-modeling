from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


MENU = """
==================== Team Building Lottery ====================
 1. Load participant list
 2. View department groups
 3. Load preset prizes
 4. Add custom prize
 5. View / reorder prizes
 6. Start lottery
 7. Show winners
 8. Export results (CSV txt)
 0. Exit
==============================================================="""


def ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Command-line interface controlling the whole lottery process."""

    def __init__(self, input_func=input, output=print) -> None:
        self._input = input_func
        self._out = output
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.list_loaded = False
        self.lottery_run = False
        self.last_prizes: list[Prize] = []

    # ----------------------------------------------------------- helpers
    def _print(self, text: str = "") -> None:
        self._out(text)

    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _group_names(self) -> list[str]:
        return sorted(self.list_manager.get_group_info(self.users).keys())

    # -------------------------------------------------------------- main
    def run(self) -> None:
        self._print("Welcome to the Team Building Smart Lottery System.")
        try:
            while True:
                self._print(MENU)
                choice = self._ask("Select an option: ").strip()
                if choice == "1":
                    self.load_list()
                elif choice == "2":
                    self.view_groups()
                elif choice == "3":
                    self.load_presets()
                elif choice == "4":
                    self.add_prize()
                elif choice == "5":
                    self.view_and_reorder_prizes()
                elif choice == "6":
                    self.start_lottery()
                elif choice == "7":
                    self.show_winners()
                elif choice == "8":
                    self.export_results()
                elif choice == "0":
                    self._print("Goodbye.")
                    break
                else:
                    self._print("Invalid option, please try again.")
        except (EOFError, KeyboardInterrupt):
            self._print("\nExiting.")

    # ------------------------------------------------------- list module
    def load_list(self) -> None:
        self._print("1) Built-in default list")
        self._print("2) Custom txt file (each line: Name,Department Group)")
        choice = self._ask("Select source: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            self._print("Invalid source selection.")
            return

        for error in errors:
            self._print(error)

        valid, duplicates = self.list_manager.validate_users(users)
        for dup in duplicates:
            self._print(f"Duplicate Name: '{dup.name}' ({dup.department}) - repeated entry")

        if errors or duplicates:
            self._print("1) Remove invalid / duplicate data and continue")
            self._print("2) Terminate upload")
            action = self._ask("Select action: ").strip()
            if action != "1":
                self._print("List upload terminated. No changes made.")
                return

        if not valid:
            self._print("No valid participants found. List not loaded.")
            return

        self.users = valid
        self.list_loaded = True
        self._print(f"Loaded {len(valid)} valid participants.")
        self.view_groups()

    def view_groups(self) -> None:
        if not self.list_loaded:
            self._print("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("Department groups:")
        for group in sorted(info):
            self._print(f"  - {group}: {info[group]} people")

    # ----------------------------------------------------- prize module
    def load_presets(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            self._print(error)
        self._print("Preset prizes loaded.")

    def _parse_groups(self, raw: str) -> list[str] | None:
        groups_list = self._group_names()
        tokens = [t.strip() for t in raw.replace("\uff0c", ",").split(",") if t.strip()]
        result: list[str] = []
        for token in tokens:
            if token.isdigit() and groups_list and 1 <= int(token) <= len(groups_list):
                group = groups_list[int(token) - 1]
            elif token.isdigit() and groups_list:
                self._print(f"Invalid group number: {token}")
                return None
            else:
                group = token
            if group not in result:
                result.append(group)
        return result

    def add_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        if not name:
            self._print("Prize name must not be empty.")
            return
        qty_raw = self._ask("Quantity: ").strip()
        if not qty_raw.isdigit() or int(qty_raw) <= 0:
            self._print("Quantity must be a positive integer.")
            return
        quantity = int(qty_raw)

        groups_list = self._group_names()
        if groups_list:
            self._print("Department groups:")
            for idx, group in enumerate(groups_list, 1):
                self._print(f"  {idx}. {group}")
        raw_groups = self._ask(
            "Avoid groups (comma-separated numbers or names, blank for none): "
        )
        avoid = self._parse_groups(raw_groups)
        if avoid is None:
            return

        drawer = self._ask("Associated lottery person (blank for none): ").strip() or None

        try:
            self.prize_manager.add_prize(name, quantity, avoid, drawer)
        except ValueError as exc:
            self._print(f"Error: {exc}")
            return
        self._print(f"Prize '{name}' added.")

    def view_and_reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print_prizes(prizes)
        raw = self._ask("Enter new order as serial numbers (e.g. '2 1 3'), blank to keep: ").strip()
        if not raw:
            return
        try:
            order = [int(t) for t in raw.replace(",", " ").split()]
        except ValueError:
            self._print("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize sequence updated.")
            self._print_prizes(self.prize_manager.get_prizes())
        else:
            self._print("Invalid order: must be a permutation of all serial numbers.")

    def _print_prizes(self, prizes: list[Prize]) -> None:
        self._print("Lottery sequence:")
        for idx, prize in enumerate(prizes, 1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._print(
                f"  {idx}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {avoid} | lottery person: {drawer}"
            )

    # ------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.list_loaded:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return

        self.result_manager = ResultManager()
        self.last_prizes = prizes
        lottery = LotteryManager(self.users)
        self.lottery_run = True

        total_rounds = len(prizes)
        for idx, prize in enumerate(prizes, 1):
            self._print("")
            self._print(f"----- Round {idx}/{total_rounds}: {prize.name} -----")
            self._print(f"Quantity: {prize.quantity}")
            self._print(f"Rule: {lottery.describe_rule(prize)}")

            lottery.start_round(prize)
            status = self._run_round(lottery, prize)
            winners = lottery.end_round()

            self._print(f"Round results ({prize.name}):")
            if winners:
                for order, user in enumerate(winners, 1):
                    self._print(f"  {order}. {user.name} ({user.department})")
            else:
                self._print("  No winners in this round.")
            if status == "terminated":
                self._print("Round terminated by operator; moving to next round.")
            elif status == "exhausted":
                self._print("No eligible participants remain for this prize; round skipped.")

        self._print("")
        self._print("================ Lottery finished ================")
        self.show_winners()

    def _run_round(self, lottery: LotteryManager, prize: Prize) -> str:
        drawn = 0
        while drawn < prize.quantity:
            nxt = ordinal(drawn + 1)
            cmd = self._ask(
                f"[Enter] draw the {nxt} winner | 'pause' | 'terminate': "
            ).strip().lower()

            if cmd == "terminate":
                return "terminated"
            if cmd == "pause":
                self._print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    sub = self._ask("(paused) > ").strip().lower()
                    if sub == "continue":
                        self._print("Lottery resumed.")
                        break
                    if sub == "terminate":
                        return "terminated"
                    self._print("Unknown command. Use 'continue' or 'terminate'.")
                continue
            if cmd != "":
                self._print("Unknown command.")
                continue

            self._print(f"Currently drawing the {nxt} winner...")
            user = lottery.draw_next()
            if user is None:
                return "exhausted"
            drawn += 1
            self.result_manager.add_winner(user, prize)
            self._print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")
        return "completed"

    # ------------------------------------------------------- results
    def show_winners(self) -> None:
        if not self.lottery_run:
            self._print("No lottery results yet.")
            return
        prizes = self.last_prizes
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._print("")
        self._print("Complete winner list:")
        self._print(f"{'Name':<20} {'Department':<28} Prize")
        total = 0
        for prize in prizes:
            for winner in grouped.get(prize.name, []):
                total += 1
                self._print(f"{winner.name:<20} {winner.department:<28} {winner.prize_name}")
        if total == 0:
            self._print("  (no winners)")

    def export_results(self) -> None:
        if not self.lottery_run:
            self._print("No lottery results to export.")
            return
        success, message = self.result_manager.export_to_csv(self.last_prizes)
        self._print(message)


def main() -> None:
    LotteryCLI().run()
