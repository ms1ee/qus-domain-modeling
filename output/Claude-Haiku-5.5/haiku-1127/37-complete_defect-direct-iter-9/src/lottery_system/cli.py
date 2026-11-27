"""Command-line interaction for the team building smart lottery system."""

from __future__ import annotations

from collections.abc import Callable

from lottery_system.default_data import CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI
from lottery_system.models import Prize, User, normalize_key
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(n: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 11th."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self._input = input_func
        self._output = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self._completed_prizes: set[str] = set()

    # ----- I/O helpers ---------------------------------------------------
    def _say(self, text: str = "") -> None:
        self._output(text)

    def _ask(self, prompt: str) -> str:
        return self._input(prompt).strip()

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        self._say("=== Team Building Smart Lottery System ===")
        try:
            while True:
                self._print_menu()
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self._load_participants()
                elif choice == "2":
                    self._show_group_info()
                elif choice == "3":
                    self._prize_menu()
                elif choice == "4":
                    self._reorder_prizes()
                elif choice == "5":
                    self._start_lottery()
                elif choice == "6":
                    self._print_summary()
                elif choice == "7":
                    self._export()
                elif choice == "0":
                    self._say("Goodbye!")
                    return
                else:
                    self._say("Invalid option, please try again.")
        except (EOFError, KeyboardInterrupt):
            self._say("\nExiting the lottery system.")

    def _print_menu(self) -> None:
        self._say("")
        self._say("1. Load participant list (default / custom txt)")
        self._say("2. View department groups and headcounts")
        self._say("3. Prize configuration")
        self._say("4. Reorder lottery rounds")
        self._say("5. Start lottery")
        self._say("6. View winner summary")
        self._say("7. Export winner list (CSV txt)")
        self._say("0. Exit")

    # ----- participants --------------------------------------------------
    def _load_participants(self) -> None:
        if self.result_manager.get_winners():
            self._say("Cannot reload the participant list after the lottery has started.")
            return
        self._say("1. Built-in default list")
        self._say("2. Custom txt list (each line: Name,Department Group)")
        choice = self._ask("Select source: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter the txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            self._say("Cancelled.")
            return

        valid, duplicates = self.list_manager.validate_users(users)
        if errors or duplicates:
            self._say("Problems detected in the list:")
            for error in errors:
                self._say(f"  - {error}")
            for dup in duplicates:
                self._say(f"  - Duplicate name ignored: {dup.name} ({dup.department})")
            self._say(
                "Type 'remove' to delete invalid/duplicate entries and continue, "
                "or 'terminate' to cancel the upload."
            )
            decision = self._ask("Your choice: ").lower()
            if decision != "remove":
                self._say("Upload terminated. The participant list was not changed.")
                return

        if not valid:
            self._say("No valid participants loaded.")
            return
        self.users = valid
        self.lottery = None
        self._say(f"Loaded {len(valid)} participants.")

    def _show_group_info(self) -> None:
        if not self.users:
            self._say("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say("Department groups:")
        for group, count in info.items():
            self._say(f"  {group}: {count} people")

    def _known_groups(self) -> set[str]:
        return {normalize_key(group) for group in self.list_manager.get_group_info(self.users)}

    # ----- prizes --------------------------------------------------------
    def _prize_menu(self) -> None:
        self._say("a. Load preset prizes")
        self._say("b. Add custom prize")
        self._say("c. Set avoidance groups for a prize")
        self._say("d. Show prizes")
        choice = self._ask("Select: ").lower()
        if choice == "a":
            for error in self.prize_manager.load_default_prizes():
                self._say(error)
            self._say("Preset prizes loaded.")
        elif choice == "b":
            self._add_custom_prize()
        elif choice == "c":
            self._set_avoid_groups()
        elif choice == "d":
            self._show_prizes()
        else:
            self._say("Invalid option.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            self._say(
                f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {avoid} | Lottery person: {drawer}"
            )

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        try:
            quantity = int(self._ask("Quantity: "))
        except ValueError:
            self._say("Quantity must be an integer.")
            return
        groups_text = self._ask("Avoidance groups (comma separated, blank for none): ")
        groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        drawer = self._ask("Associated lottery person (blank for none): ") or None
        known = self._known_groups()
        for group in groups:
            if known and normalize_key(group) not in known:
                self._say(f"Warning: group '{group}' is not in the current participant list.")
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._say(f"Failed to add prize: {exc}")
            return
        self._say(f"Prize added: {prize.name}")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask("Enter prize number: ")
        try:
            index = int(text)
        except ValueError:
            self._say("Invalid prize number.")
            return
        if not 1 <= index <= len(prizes):
            self._say("Invalid prize number.")
            return
        groups_text = self._ask("Avoidance groups (comma separated, blank for none): ")
        groups = [group.strip() for group in groups_text.split(",") if group.strip()]
        prize = prizes[index - 1]
        prize.avoid_groups = []
        for group in groups:
            if group and normalize_key(group) not in {normalize_key(g) for g in prize.avoid_groups}:
                prize.avoid_groups.append(group)
        self._say(f"Avoidance groups for '{prize.name}' set to: {', '.join(prize.avoid_groups) or 'None'}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(item) for item in text.split()]
        except ValueError:
            self._say("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Prize order updated.")
            self._show_prizes()
        else:
            self._say("Invalid order: each prize number must appear exactly once.")

    # ----- lottery -------------------------------------------------------
    def _start_lottery(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not self.users:
            self._say("Please load the participant list first.")
            return
        if not prizes:
            self._say("Please configure prizes first.")
            return
        if self.lottery is None:
            self.lottery = LotteryManager(self.users)
        pending = [prize for prize in prizes if prize.name not in self._completed_prizes]
        if not pending:
            self._say("All lottery rounds have already been completed.")
            return
        self._say("=== Lottery started ===")
        self._say("During a round: press Enter to draw the next winner, "
                  "type 'pause' to interrupt, 'terminate' to skip the round.")
        for prize in pending:
            self._run_round(prize)
            self._completed_prizes.add(prize.name)
        self._say("=== All lottery rounds completed ===")

    def _run_round(self, prize: Prize) -> None:
        assert self.lottery is not None
        self._say("")
        self._say(f"--- Round: {prize.name} ---")
        self._say(f"Quantity: {prize.quantity}")
        self._say(f"Rule: {self.lottery.describe_rule(prize)}")

        winners: list[User] = []
        while len(winners) < prize.quantity:
            command = self._ask("[Enter]=draw next | pause | terminate: ").lower()
            if command == "pause":
                if not self._wait_while_paused():
                    self._say("Round terminated by operator.")
                    break
            elif command == "terminate":
                self._say("Round terminated by operator.")
                break
            elif command != "":
                self._say("Unknown command.")
                continue

            user = self.lottery.draw_one(prize)
            if user is None:
                self._say("No eligible candidates remain. The round ends early.")
                break
            self.result_manager.add_winner(user, prize)
            winners.append(user)
            self._say(f"Currently drawing the {ordinal(len(winners))} winner...")
            self._say(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.lottery.finish_round(prize, winners)
        self._say(f"Round results for {prize.name}:")
        if not winners:
            self._say("  (no winners)")
        for index, user in enumerate(winners, start=1):
            self._say(f"  {index}. {user.name} ({user.department})")

    def _wait_while_paused(self) -> bool:
        """Block until 'continue' (returns True) or 'terminate' (returns False)."""
        self._say("Lottery paused. Type 'continue' to resume or 'terminate' to skip this round.")
        while True:
            command = self._ask("paused> ").lower()
            if command == "continue":
                self._say("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._say("While paused, only 'continue' or 'terminate' is accepted.")

    # ----- results -------------------------------------------------------
    def _print_summary(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._say("=== Winner list ===")
        for prize in prizes:
            self._say(f"[{prize.name}]")
            winners = grouped.get(prize.name, [])
            if not winners:
                self._say("  (no winners yet)")
            for winner in winners:
                self._say(f"  {winner.user.name} | {winner.user.department} | {prize.name}")

    def _export(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        _, message = self.result_manager.export_to_csv(prizes)
        self._say(message)


def main() -> None:
    """Start the interactive command-line lottery system."""
    LotterySystemCLI().run()


if __name__ == "__main__":
    main()
