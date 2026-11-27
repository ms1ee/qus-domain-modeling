"""Command-line interface for the team building lottery system."""

from __future__ import annotations

from collections.abc import Callable

from lottery_system.constants import LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner

SEPARATOR = "-" * 60


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def describe_rules(prize: Prize) -> str:
    """Build a human-readable rule description for a prize round."""
    rules = ["previous winners are excluded"]
    drawer = prize.associated_drawer
    if drawer == LI_BIN:
        rules.append("special rule for Li Bin: avoidance groups are not applied")
    elif prize.avoid_groups:
        rules.append(
            "avoidance groups "
            + ", ".join(prize.avoid_groups)
            + " are drawn after other members"
        )
    if drawer == MA_JIAQI:
        rules.append(
            "Cheng Ru Group protection may limit the pool to Cheng Ru Group members"
        )
    if drawer:
        rules.append(f"associated lottery person: {drawer}")
    return "; ".join(rules)


class LotterySystemCLI:
    """Interactive console application."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[..., None] = print,
    ) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.completed_prizes: set[str] = set()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    def _choose(self, prompt: str, options: set[str]) -> str:
        while True:
            value = self._ask(prompt).lower()
            if value in options:
                return value
            self._print("Invalid input, please try again.")

    def _ensure_lottery(self) -> LotteryManager:
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
            for winner in self.result_manager.get_all_winners():
                self.lottery.mark_as_winner(winner.user)
        return self.lottery

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def _print_menu(self) -> None:
        self._print("\n========== Team Building Smart Lottery ==========")
        self._print("1. Load participant list")
        self._print("2. View department groups")
        self._print("3. Configure prizes")
        self._print("4. Start lottery")
        self._print("5. View winners")
        self._print("6. Export winners (CSV txt)")
        self._print("0. Exit")

    def run(self) -> None:
        while True:
            self._print_menu()
            choice = self._ask("Select an option: ")
            if choice == "1":
                self.load_list_menu()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.run_lottery()
            elif choice == "5":
                self.show_results()
            elif choice == "6":
                self.export_results()
            elif choice == "0":
                self._print("Goodbye!")
                break
            else:
                self._print("Invalid option, please try again.")

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------
    def load_list_menu(self) -> None:
        self._print("\n[Load Participant List]")
        self._print("1. Built-in default list")
        self._print("2. Custom txt file (format: Name,Department per line)")
        self._print("0. Cancel")
        choice = self._ask("Select: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            if not path:
                self._print("Path is empty. Upload cancelled.")
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        if errors:
            self._print(f"Found {len(errors)} problematic line(s):")
            for error in errors:
                self._print(f"  {error}")
            action = self._choose(
                "Enter 'r' to remove invalid data and continue, "
                "or 't' to terminate upload: ",
                {"r", "t"},
            )
            if action == "t":
                self._print("Upload terminated. Current list unchanged.")
                return

        valid_users, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._print(f"Found {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                self._print(f"  Duplicate: {user.name} ({user.department})")
            action = self._choose(
                "Enter 'r' to remove duplicates and continue, "
                "or 't' to terminate upload: ",
                {"r", "t"},
            )
            if action == "t":
                self._print("Upload terminated. Current list unchanged.")
                return

        if not valid_users:
            self._print("No valid participants found. List not loaded.")
            return

        self.users = valid_users
        self.lottery = None
        self._print(f"Loaded {len(valid_users)} participant(s).")
        self.show_groups()

    def show_groups(self) -> None:
        if not self.users:
            self._print("No participant list loaded yet.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("\n[Department Groups]")
        for department, count in info.items():
            self._print(f"  {department}: {count} person(s)")
        self._print(f"  Total: {len(self.users)} person(s)")

    # ------------------------------------------------------------------
    # Prize configuration
    # ------------------------------------------------------------------
    def prize_menu(self) -> None:
        while True:
            self._print("\n[Prize Configuration]")
            self._print("1. Load preset prizes")
            self._print("2. Add custom prize")
            self._print("3. Set avoidance groups for a prize")
            self._print("4. Reorder lottery rounds")
            self._print("5. View prizes")
            self._print("0. Back")
            choice = self._ask("Select: ")
            if choice == "1":
                self._load_default_prizes()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self.show_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured yet.")
            return
        self._print("\n[Prize Order]")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            self._print(
                f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoidance groups: {groups} | Associated person: {drawer}"
            )

    def _load_default_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                self._print(f"  Skipped: {error}")
        else:
            self._print("Preset prizes loaded.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._print("Quantity must be an integer. Prize not added.")
            return
        groups_text = self._ask(
            "Avoidance groups (comma-separated, empty for none): "
        )
        groups = [g.strip() for g in groups_text.split(",") if g.strip()]
        drawer = self._ask("Associated lottery person (empty for none): ") or None
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._print(f"Failed to add prize: {exc}")
            return
        self._print(f"Prize '{name.strip()}' added.")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured yet.")
            return
        self.show_prizes()
        text = self._ask("Enter prize serial number: ")
        try:
            index = int(text)
        except ValueError:
            self._print("Invalid serial number.")
            return
        if not 1 <= index <= len(prizes):
            self._print("Serial number out of range.")
            return
        groups_text = self._ask(
            "Avoidance groups (comma-separated, empty to clear): "
        )
        groups = [g.strip() for g in groups_text.split(",") if g.strip()]
        if self.prize_manager.set_avoid_groups(prizes[index - 1].name, groups):
            self._print("Avoidance groups updated.")
        else:
            self._print("Failed to update avoidance groups.")

    def _reorder_prizes(self) -> None:
        if not self.prize_manager.get_prizes():
            self._print("No prizes configured yet.")
            return
        self.show_prizes()
        text = self._ask(
            "Enter new order as serial numbers separated by spaces (e.g. 2 1 3): "
        )
        try:
            order = [int(part) for part in text.split()]
        except ValueError:
            self._print("Order must contain only serial numbers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize order updated.")
        else:
            self._print("Invalid order. Each serial number must appear exactly once.")

    # ------------------------------------------------------------------
    # Lottery process
    # ------------------------------------------------------------------
    def run_lottery(self) -> None:
        if not self.users:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return
        pending = [p for p in prizes if p.name not in self.completed_prizes]
        if not pending:
            self._print("All lottery rounds have already been completed.")
            return
        if self._ask("Start the lottery now? (y/n): ").lower() not in ("y", "yes"):
            return

        lottery = self._ensure_lottery()
        self._print(f"Lottery started with {len(prizes)} round(s).")
        for round_no, prize in enumerate(prizes, start=1):
            if prize.name in self.completed_prizes:
                continue
            self._run_round(round_no, prize, lottery)
            self.completed_prizes.add(prize.name)
        self._print("\nAll lottery rounds finished. Use option 5 to view winners.")

    def _run_round(self, round_no: int, prize: Prize, lottery: LotteryManager) -> None:
        self._print(SEPARATOR)
        self._print(f"Round {round_no}: {prize.name}")
        self._print(f"Quantity: {prize.quantity}")
        self._print(f"Rules: {describe_rules(prize)}")
        self._print(SEPARATOR)
        self._print(
            "Commands: Enter = draw next, 'pause' = pause, 'terminate' = skip round"
        )

        round_winners: list[Winner] = []
        drawn = 0
        paused = False
        while drawn < prize.quantity:
            if paused:
                command = self._ask(
                    "[PAUSED] Type 'continue' to resume or 'terminate' to skip: "
                ).lower()
                if command == "continue":
                    paused = False
                    self._print("Lottery resumed.")
                elif command == "terminate":
                    self._print("Current round terminated.")
                    break
                else:
                    self._print("Unknown command.")
                continue

            command = self._ask("Draw next winner (Enter / pause / terminate): ").lower()
            if command == "pause":
                paused = True
                self._print("Lottery paused.")
                continue
            if command == "terminate":
                self._print("Current round terminated.")
                break
            if command not in ("", "continue"):
                self._print("Unknown command.")
                continue

            self._print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            winner_user = lottery.draw(prize)
            if winner_user is None:
                self._print("No eligible candidates remain for this round.")
                break
            drawn += 1
            winner = self.result_manager.add_winner(winner_user, prize)
            round_winners.append(winner)
            self._print(
                f"Congratulations {winner_user.name} ({winner_user.department}) "
                f"for winning {prize.name}"
            )

        self._print(f"\nRound {round_no} finished: {drawn}/{prize.quantity} awarded.")
        if round_winners:
            self._print("Round results (winning order):")
            for winner in round_winners:
                self._print(
                    f"  {winner.sequence}. {winner.user.name} "
                    f"({winner.user.department})"
                )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def show_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        if not any(grouped.values()):
            self._print("No winners yet.")
            return
        self._print("\n[Winner List]")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self._print(f"\n{prize_name}")
            for winner in winners:
                self._print(
                    f"  {winner.sequence}. {winner.user.name} "
                    f"({winner.user.department})"
                )

    def export_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        _, message = (None, None)
        success, message = self.result_manager.export_to_csv(prizes)
        self._print(message if success else f"Error: {message}")


def main() -> None:
    """Entry point for the console application."""
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
