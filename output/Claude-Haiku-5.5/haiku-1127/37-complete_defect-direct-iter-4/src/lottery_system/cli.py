"""Command-line interaction for the lottery system."""
from __future__ import annotations

from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import (
    CHEN_QIXIAN,
    JIN_DUO,
    LI_BIN,
    MA_JIAQI,
    LotteryManager,
)
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

DRAWER_CHOICES: list[str] = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive command-line application."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    # --------------------------------------------------------------- main menu
    def run(self) -> None:
        print("=== Company Team Building Smart Lottery System ===")
        while True:
            print("\nMain Menu:")
            print("  1. Load participant list")
            print("  2. View department groups")
            print("  3. Prize configuration")
            print("  4. Start lottery")
            print("  0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._load_participants()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self._prize_menu()
            elif choice == "4":
                self._start_lottery()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option.")

    # ------------------------------------------------------------ list module
    def _load_participants(self) -> None:
        print("Participant list source:")
        print("  1. Built-in default team building list")
        print("  2. Custom txt file (each line: Name,Department Group)")
        choice = self._ask("Select source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip("\"'")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            print("Cancelled.")
            return

        valid, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate Entry: '{u.name}' ({u.department}) already appears earlier in the list"
            for u in duplicates
        )

        if problems:
            print(f"Found {len(problems)} problem(s):")
            for problem in problems:
                print(f"  - {problem}")
            print("  r. Remove invalid/duplicate data and continue with the valid users")
            print("  q. Terminate upload")
            decision = self._ask("Choose (r/q): ").lower()
            if decision != "r":
                print("Upload terminated. Participant list unchanged.")
                return

        if not valid:
            print("No valid participants found. Participant list unchanged.")
            return

        self.users = valid
        print(f"Loaded {len(valid)} participants.")
        self._show_groups()

    def _show_groups(self) -> None:
        if not self.users:
            print("No participants loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"Department groups ({len(info)}):")
        for department, count in info.items():
            print(f"  - {department}: {count} people")

    # ---------------------------------------------------------- prize module
    def _prize_menu(self) -> None:
        while True:
            print("\nPrize Configuration:")
            print("  1. Load preset prize library")
            print("  2. Add custom prize")
            print("  3. Reorder prizes (lottery sequence)")
            print("  4. View prizes")
            print("  0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._load_default_prizes()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._reorder_prizes()
            elif choice == "4":
                self._show_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        for error in errors:
            print(f"  - {error}")
        if not errors:
            print("Preset prize library loaded.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            print("Quantity must be an integer.")
            return

        print("Associated lottery person:")
        for index, drawer in enumerate(DRAWER_CHOICES, start=1):
            print(f"  {index}. {drawer}")
        drawer_text = self._ask("Enter number, a name, or blank for none: ")
        drawer: str | None = None
        if drawer_text:
            if drawer_text.isdigit():
                idx = int(drawer_text)
                if 1 <= idx <= len(DRAWER_CHOICES):
                    drawer = DRAWER_CHOICES[idx - 1]
                else:
                    print("Invalid lottery person number.")
                    return
            else:
                drawer = drawer_text

        if self.users:
            known = ", ".join(self.list_manager.get_group_info(self.users).keys())
            print(f"Known department groups: {known}")
        groups_text = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [g.strip() for g in groups_text.split(",") if g.strip()]

        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Failed to add prize: {exc}")
            return
        print(f"Prize '{name.strip()}' added.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prizes (lottery sequence):")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "-"
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "-"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Drawer: {drawer} | Avoid: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask("Enter new sequence as serial numbers (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: use integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
            self._show_prizes()
        else:
            print("Invalid ordering: each prize number must appear exactly once.")

    # ------------------------------------------------------- lottery process
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return

        lottery = LotteryManager(self.users)
        results = ResultManager()

        print("\n=== Lottery started ===")
        for index, prize in enumerate(prizes, start=1):
            print(f"\n--- Round {index}/{len(prizes)}: {prize.name} ---")
            print(f"Quantity: {prize.quantity}")
            print(f"Rule: {lottery.describe_rules(prize)}")
            self._run_round(lottery, results, prize)
            self._print_round_results(results, prize)

        self._show_final_summary(results, prizes)

    def _run_round(self, lottery: LotteryManager, results: ResultManager, prize: Prize) -> None:
        drawn = 0
        paused = False
        try:
            while drawn < prize.quantity:
                if paused:
                    command = self._ask("[PAUSED] Type 'continue' to resume or 'terminate' to end this round: ").lower()
                    if command == "continue":
                        paused = False
                        print("Lottery resumed.")
                    elif command == "terminate":
                        print(f"Round '{prize.name}' terminated early.")
                        return
                    else:
                        print("Unknown command.")
                    continue

                command = self._ask(
                    "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
                ).lower()
                if command == "pause":
                    paused = True
                    print("Lottery paused.")
                    continue
                if command == "terminate":
                    print(f"Round '{prize.name}' terminated early.")
                    return
                if command != "":
                    print("Unknown command.")
                    continue

                print(f"Currently drawing the {_ordinal(drawn + 1)} winner...")
                winner = lottery.draw_winner(prize)
                if winner is None:
                    print("No eligible candidates remain for this prize. Round ends.")
                    return
                drawn += 1
                results.add_winner(winner, prize)
                print(
                    f"Congratulations {winner.name} ({winner.department}) "
                    f"for winning {prize.name}!"
                )
        finally:
            lottery.finish_round(prize)

    def _print_round_results(self, results: ResultManager, prize: Prize) -> None:
        winners = results.get_winners_by_prize([prize])[prize.name]
        print(f"\nRound results for '{prize.name}':")
        if not winners:
            print("  (no winners)")
            return
        for position, winner in enumerate(winners, start=1):
            print(f"  {position}. {winner.user.name} ({winner.user.department})")

    def _show_final_summary(self, results: ResultManager, prizes: list[Prize]) -> None:
        print("\n=== Lottery finished. Complete winner list ===")
        by_prize = results.get_winners_by_prize(prizes)
        if not any(by_prize.values()):
            print("No winners were drawn.")
            return
        print(f"{'Name':<20} {'Department':<28} Prize")
        for prize in prizes:
            for winner in by_prize.get(prize.name, []):
                print(f"{winner.user.name:<20} {winner.user.department:<28} {winner.prize_name}")

        answer = self._ask("Export the winner list to a txt (CSV format) file? (y/n): ").lower()
        if answer == "y":
            _, message = results.export_to_csv(prizes)
            print(message)


def main() -> None:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
