"""Command-line interface for controlling the team building lottery."""

from lottery_system.models import LI_BIN, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, sort_prizes_by_level


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self, input_func=input, output_func=print) -> None:
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.results: ResultManager | None = None

    # ---------------------------------------------------------------- helpers
    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _out(self, text: str = "") -> None:
        self._print(text)

    # ------------------------------------------------------------- main loop
    def run(self) -> None:
        self._out("=== Team Building Smart Lottery System ===")
        while True:
            self._print_main_menu()
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self.load_list_menu()
            elif choice == "2":
                self.show_groups()
            elif choice == "3":
                self.prize_menu()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.results_menu()
            elif choice == "0":
                self._out("Goodbye.")
                break
            else:
                self._out("Invalid option, please try again.")

    def _print_main_menu(self) -> None:
        self._out("")
        self._out("---------- Main Menu ----------")
        self._out("1. Load participant list")
        self._out("2. View department groups")
        self._out("3. Prize configuration")
        self._out("4. Start lottery")
        self._out("5. Results (summary / export)")
        self._out("0. Exit")

    # ------------------------------------------------------------ list menus
    def load_list_menu(self) -> None:
        self._out("1. Built-in default list")
        self._out("2. Custom txt list (format: Name,Department per line)")
        self._out("0. Cancel")
        choice = self._ask("Select list source: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ").strip()
            users, errors = self.list_manager.load_custom_list(path)
        else:
            self._out("Cancelled.")
            return
        self._verify_and_apply(users, errors)

    def _verify_and_apply(self, users: list[User], errors: list[str]) -> None:
        valid, duplicates = self.list_manager.validate_users(users)
        if not errors and not duplicates:
            self.users = valid
            self._out(f"List loaded successfully: {len(valid)} participants.")
            return

        self._out("List verification found problems:")
        for error in errors:
            self._out(f"  {error}")
        for dup in duplicates:
            self._out(f"  Duplicate name: {dup.name} ({dup.department})")
        self._out(
            f"Valid participants: {len(valid)}. "
            "Type 'r' to remove invalid data and continue, or 'q' to terminate the upload."
        )
        while True:
            command = self._ask("Your choice (r/q): ").strip().lower()
            if command == "r":
                self.users = valid
                self._out(f"Invalid data removed. Loaded {len(valid)} participants.")
                return
            if command == "q":
                self._out("Upload terminated. Previous list kept.")
                return
            self._out("Please enter 'r' or 'q'.")

    def show_groups(self) -> None:
        if not self.users:
            self._out("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._out("Current department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._out(f"  {index}. {department}: {count} people")

    # ----------------------------------------------------------- prize menus
    def prize_menu(self) -> None:
        while True:
            self._out("")
            self._out("---------- Prize Configuration ----------")
            self._out("1. View prizes")
            self._out("2. Load preset prizes")
            self._out("3. Add custom prize")
            self._out("4. Set avoidance groups / drawer for a prize")
            self._out("5. Reorder lottery sequence")
            self._out("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                self.show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._out(f"  {error}")
                self._out("Preset prizes loaded.")
            elif choice == "3":
                self.add_prize_interactive()
            elif choice == "4":
                self.set_prize_rules_interactive()
            elif choice == "5":
                self.reorder_interactive()
            elif choice == "0":
                return
            else:
                self._out("Invalid option, please try again.")

    def show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("No prizes configured.")
            return
        self._out("Lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            self._out(f"  {index}. {self._describe_prize_line(prize)}")

    def _describe_prize_line(self, prize: Prize) -> str:
        drawer = prize.associated_drawer or "None"
        avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        return (
            f"{prize.name} | Quantity: {prize.quantity} | "
            f"Lottery person: {drawer} | Avoid groups: {avoid}"
        )

    def add_prize_interactive(self) -> None:
        name = self._ask("Prize name: ").strip()
        quantity = self._ask_positive_int("Quantity: ")
        if quantity is None:
            return
        avoid_text = self._ask(
            "Avoidance groups (comma separated, blank for none): "
        ).strip()
        avoid = [g.strip() for g in avoid_text.split(",") if g.strip()]
        drawer = self._ask("Associated lottery person (blank for none): ").strip()
        try:
            prize = self.prize_manager.add_prize(name, quantity, avoid, drawer or None)
            self._out(f"Prize added: {prize.name}")
        except ValueError as exc:
            self._out(f"Cannot add prize: {exc}")

    def set_prize_rules_interactive(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("No prizes configured.")
            return
        self.show_prizes()
        index = self._ask_index("Prize serial number: ", len(prizes))
        if index is None:
            return
        prize = prizes[index]
        avoid_text = self._ask(
            "Avoidance groups (comma separated, blank for none): "
        ).strip()
        prize.avoid_groups = [g.strip() for g in avoid_text.split(",") if g.strip()]
        drawer = self._ask("Associated lottery person (blank for none): ").strip()
        prize.associated_drawer = drawer or None
        self._out("Prize rules updated.")

    def reorder_interactive(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("No prizes configured.")
            return
        self.show_prizes()
        text = self._ask(
            "Enter the new order as serial numbers separated by spaces (blank to cancel): "
        ).strip()
        if not text:
            return
        try:
            order = [int(token) for token in text.split()]
        except ValueError:
            self._out("Invalid input: please enter integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._out("Lottery sequence updated.")
            self.show_prizes()
        else:
            self._out("Invalid order: must contain every serial number exactly once.")

    def _ask_positive_int(self, prompt: str) -> int | None:
        for _ in range(3):
            text = self._ask(prompt).strip()
            if text.isdigit() and int(text) > 0:
                return int(text)
            self._out("Please enter a positive integer.")
        self._out("Too many invalid attempts; cancelled.")
        return None

    def _ask_index(self, prompt: str, size: int) -> int | None:
        text = self._ask(prompt).strip()
        if text.isdigit() and 1 <= int(text) <= size:
            return int(text) - 1
        self._out("Invalid serial number.")
        return None

    # ---------------------------------------------------------------- lottery
    def start_lottery(self) -> None:
        if not self.users:
            self._out("Please load the participant list first (option 1).")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._out("Please configure prizes first (option 3).")
            return
        if self.results is not None and self.results.get_winners():
            self._out("Starting a new lottery: previous results are cleared.")

        self.results = ResultManager()
        lottery = LotteryManager(self.users, result_manager=self.results)
        self._out("Lottery started. During the draw you may type:")
        self._out("  Enter        -> draw the next winner")
        self._out("  pause        -> pause the lottery")
        self._out("  terminate    -> end the current round and skip to the next")

        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(lottery, prize, round_no)

        self._out("")
        self._out("All rounds completed.")
        self._show_summary(prizes)

    def _rule_description(self, lottery: LotteryManager, prize: Prize) -> str:
        parts: list[str] = []
        if lottery.is_relaxed_prize(prize):
            parts.append(
                f"Relaxed rules ({LI_BIN}): only previous winners are excluded"
            )
        else:
            text = "Excludes previous winners"
            if prize.avoid_groups:
                text += " and members of groups: " + ", ".join(prize.avoid_groups)
            parts.append(text)
        if lottery.is_cheng_ru_protection_active(prize):
            parts.append("Cheng Ru group protection active: only Cheng Ru Group members eligible")
        if prize.associated_drawer:
            parts.append(f"Lottery person: {prize.associated_drawer}")
        return "; ".join(parts)

    def _run_round(self, lottery: LotteryManager, prize: Prize, round_no: int) -> None:
        self._out("")
        self._out(
            f"=== Round {round_no}: {prize.name} | Quantity: {prize.quantity} | "
            f"Rule: {self._rule_description(lottery, prize)} ==="
        )
        round_winners: list[User] = []
        index = 1
        while index <= prize.quantity:
            command = self._ask(
                f"Press Enter to draw the {_ordinal(index)} winner (pause / terminate): "
            ).strip().lower()
            if command == "pause":
                if not self._wait_for_resume():
                    self._out("Round terminated.")
                    break
            elif command == "terminate":
                self._out("Round terminated.")
                break
            elif command:
                self._out("Unknown command.")
                continue

            self._out(f"Currently drawing the {_ordinal(index)} winner...")
            user = lottery.draw_once(prize)
            if user is None:
                self._out("No eligible candidates remain for this prize; round ends.")
                break
            round_winners.append(user)
            self._out(
                f"Congratulations {user.name} ({user.department}) for winning {prize.name}"
            )
            index += 1

        self._out(f"Round {round_no} finished. Winners this round: {len(round_winners)}")

    def _wait_for_resume(self) -> bool:
        """Block until 'continue' (True) or 'terminate' (False)."""
        self._out("Lottery paused.")
        while True:
            command = self._ask("Type 'continue' to resume or 'terminate' to end this round: ")
            command = command.strip().lower()
            if command == "continue":
                self._out("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            self._out("Please type 'continue' or 'terminate'.")

    def _show_summary(self, prizes: list[Prize]) -> None:
        if self.results is None:
            self._out("No lottery results yet.")
            return
        grouped = self.results.get_winners_by_prize(prizes)
        self._out("")
        self._out("=========== Winner List ===========")
        if not any(grouped.values()):
            self._out("No winners were drawn.")
            return
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self._out(f"[{prize_name}]")
            for winner in winners:
                self._out(
                    f"  #{winner.order} {winner.user.name} ({winner.user.department})"
                )

    # ---------------------------------------------------------------- results
    def results_menu(self) -> None:
        if self.results is None:
            self._out("No lottery results yet.")
            return
        self._out("1. Show winner summary")
        self._out("2. Export winner list to txt (CSV format)")
        self._out("0. Back")
        choice = self._ask("Select an option: ").strip()
        prizes = self.prize_manager.get_prizes()
        if choice == "1":
            self._show_summary(prizes)
        elif choice == "2":
            _, message = self.results.export_to_csv(prizes)
            self._out(message)
        else:
            return


def main() -> None:
    """Start the interactive lottery system."""
    cli = LotteryCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
