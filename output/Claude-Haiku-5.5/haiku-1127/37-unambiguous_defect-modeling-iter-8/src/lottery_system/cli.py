"""Interactive command-line interface for the team building lottery."""

from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager

MAIN_MENU = """
==============================================
   Team Building Smart Lottery System
==============================================
1. Load participant list
2. View department groups
3. Prize configuration
4. Start lottery
5. Export results
0. Exit
"""

PRIZE_MENU = """
--- Prize configuration ---
1. Add custom prize
2. Load default prize library
3. View prizes
4. Reorder prizes (lottery sequence)
0. Back
"""


def ordinal(n: int) -> str:
    """Return the English ordinal form of a positive integer (1st, 2nd, 11th...)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Drives the menu-based lottery workflow."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_prizes: list[Prize] = []

    # ----- main loop ----------------------------------------------------

    def run(self) -> None:
        try:
            while True:
                print(MAIN_MENU)
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self.load_list()
                elif choice == "2":
                    self.view_groups()
                elif choice == "3":
                    self.prize_menu()
                elif choice == "4":
                    self.start_lottery()
                elif choice == "5":
                    self.export_results()
                elif choice == "0":
                    print("Goodbye!")
                    return
                else:
                    print("Invalid option, please try again.")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")

    def _ask(self, prompt: str) -> str:
        return input(prompt).strip()

    def _ask_int(self, prompt: str, minimum: int = 1) -> int:
        while True:
            raw = self._ask(prompt)
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a whole number.")
                continue
            if value < minimum:
                print(f"Please enter a number greater than or equal to {minimum}.")
                continue
            return value

    def _reset_lottery(self) -> None:
        self.lottery = None
        self.lottery_prizes = []

    # ----- list management ----------------------------------------------

    def load_list(self) -> None:
        print("1. Built-in default team building list")
        print("2. Custom txt file (format: name,department per line)")
        mode = self._ask("Select loading mode: ")
        if mode == "1":
            users, errors = self.list_manager.load_default_list()
        elif mode == "2":
            path = self._ask("Enter the txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Invalid option.")
            return

        if errors:
            print(f"Found {len(errors)} invalid line(s):")
            for error in errors:
                print(f"  {error}")
            command = self._ask(
                "Type 'skip' to ignore invalid lines and continue, or 'cancel' to abort: "
            ).lower()
            if command != "skip":
                print("Upload cancelled.")
                return

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"Found {len(duplicates)} duplicate name(s):")
            for dup in duplicates:
                print(f"  {dup.name} ({dup.department})")
            command = self._ask(
                "Type 'remove' to drop duplicates (keep first occurrence), or 'cancel' to abort: "
            ).lower()
            if command != "remove":
                print("Upload cancelled.")
                return

        if not valid:
            print("No valid participants were loaded.")
            return

        self.users = valid
        self._reset_lottery()
        print(f"Loaded {len(valid)} participants.")

    def view_groups(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("Current department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} people")
        print(f"Total: {len(self.users)} people")

    # ----- prize configuration ------------------------------------------

    def prize_menu(self) -> None:
        while True:
            print(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._add_prize_interactive()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    print("Some default prizes could not be added:")
                    for error in errors:
                        print(f"  {error}")
                else:
                    print("Default prize library loaded.")
                self._reset_lottery()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes_interactive()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _add_prize_interactive(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_int("Quantity: ", minimum=1)
        if self.users:
            groups = ", ".join(self.list_manager.get_group_info(self.users).keys())
            print(f"Available groups: {groups}")
        avoid_raw = self._ask("Avoid groups (comma-separated, blank for none): ")
        drawer = self._ask("Associated lottery person (blank for none): ")
        avoid_groups = [g for g in avoid_raw.split(",") if g.strip()]
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid_groups, drawer or None)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        self._reset_lottery()
        print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prizes (lottery sequence):")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"avoid groups: {avoid} | lottery person: {drawer}"
            )

    def _reorder_prizes_interactive(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are required to reorder.")
            return
        self._show_prizes()
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(item) for item in raw.split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._reset_lottery()
            print("Lottery sequence updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ----- lottery process ----------------------------------------------

    def start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        self.lottery = lottery
        self.lottery_prizes = list(prizes)

        print("\n=== Lottery started ===")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(lottery, round_no, prize)

        print("\n=== Final winner list ===")
        results = lottery.result_manager.get_winners_by_prize(self.lottery_prizes)
        for prize_name, winners in results.items():
            print(f"{prize_name}:")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.user.name} ({winner.user.department})")
        print("=== Lottery finished ===")

    def _run_round(self, lottery: LotteryManager, round_no: int, prize: Prize) -> None:
        drawer = prize.associated_drawer or "Anyone"
        print(f"\n=== Round {round_no}: {prize.name} ===")
        print(f"Quantity: {prize.quantity} | Lottery person: {drawer}")
        print(f"Rules: {lottery.describe_rules(prize)}")

        round_winners: list[User] = []
        for _ in range(prize.quantity):
            if not lottery.has_eligible(prize):
                print("No eligible participants remain for this prize. Round ends.")
                break
            action = self._await_draw_command(len(round_winners) + 1)
            if action == "terminate":
                print("Round terminated. Skipping remaining draws.")
                break
            winner = lottery.draw_one(prize)
            if winner is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            round_winners.append(winner)
            print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}")

        lottery.end_round(prize)

        print(f"Round {round_no} results:")
        if round_winners:
            for index, winner in enumerate(round_winners, start=1):
                print(f"  {index}. {winner.name} ({winner.department})")
        else:
            print("  No winners in this round.")

    def _await_draw_command(self, draw_number: int) -> str:
        """Wait for the operator before the next draw.

        Returns "draw" to proceed or "terminate" to end the current round.
        """
        print(f"Currently drawing the {ordinal(draw_number)} winner...")
        while True:
            command = self._ask("[Enter]=draw | pause | terminate > ").lower()
            if command in ("", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    paused_command = self._ask("[paused] continue | terminate > ").lower()
                    if paused_command == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if paused_command == "terminate":
                        return "terminate"
                    print("Unknown command. Type 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    # ----- export -------------------------------------------------------

    def export_results(self) -> None:
        if self.lottery is None:
            print("No lottery results to export. Please run the lottery first.")
            return
        _, message = self.lottery.result_manager.export_to_csv(self.lottery_prizes)
        print(message)


def main() -> None:
    LotteryCLI().run()
