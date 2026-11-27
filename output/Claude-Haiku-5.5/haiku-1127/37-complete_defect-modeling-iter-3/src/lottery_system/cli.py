"""Command-line interface for the lottery system."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


CMD_PAUSE = "pause"
CMD_CONTINUE = "continue"
CMD_TERMINATE = "terminate"
ACTION_DRAW = "draw"


def ordinal(number: int) -> str:
    """Return the English ordinal form of a positive integer, e.g. 1st, 12th."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _split_tokens(raw: str):
    return [token.strip() for token in raw.split(",") if token.strip()]


class LotterySystemCLI:
    """Interactive command-line controller."""

    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users = []
        self.list_loaded = False
        self.lottery_manager = None
        self.result_manager = ResultManager()
        self._handlers = {
            "1": self._load_default_list,
            "2": self._load_custom_list,
            "3": self._view_groups,
            "4": self._load_preset_prizes,
            "5": self._add_prize,
            "6": self._view_prizes,
            "7": self._reorder_prizes,
            "8": self._start_lottery,
            "9": self._show_results,
            "10": self._export_results,
        }

    # ------------------------------------------------------------------ helpers
    def _ask(self, prompt: str = "") -> str:
        return self._input(prompt).strip()

    def _ask_positive_int(self, prompt: str) -> int:
        while True:
            raw = self._ask(prompt)
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            self._print("Please enter a positive whole number.")

    def _group_names(self):
        return list(self.list_manager.get_group_info(self.users).keys())

    # --------------------------------------------------------------- main loop
    def run(self) -> None:
        self._print("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                self._print_menu()
                choice = self._ask("Select an option: ")
                if choice == "0":
                    break
                handler = self._handlers.get(choice)
                if handler is None:
                    self._print("Invalid option, please try again.")
                    continue
                handler()
        except (EOFError, KeyboardInterrupt):
            self._print("\nInput closed, exiting system.")
        self._print("Goodbye!")

    def _print_menu(self) -> None:
        self._print("")
        self._print("---------------- Main Menu ----------------")
        self._print("1.  Load built-in default participant list")
        self._print("2.  Upload custom txt participant list")
        self._print("3.  View department groups")
        self._print("4.  Load preset prizes")
        self._print("5.  Add custom prize")
        self._print("6.  View prizes")
        self._print("7.  Reorder prizes")
        self._print("8.  Start lottery")
        self._print("9.  View winner list")
        self._print("10. Export winner list (CSV)")
        self._print("0.  Exit")
        self._print("-------------------------------------------")

    # ------------------------------------------------------- list management
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._finalize_list(users, errors)

    def _load_custom_list(self) -> None:
        path = self._ask("Enter the path of the custom txt list: ").strip('"')
        if not path:
            self._print("No path entered.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._finalize_list(users, errors)

    def _finalize_list(self, users, errors) -> bool:
        if errors:
            self._print(f"Found {len(errors)} invalid record(s):")
            for error in errors:
                self._print("  - " + error)
            choice = self._ask(
                "Enter 'c' to skip invalid records and continue, or 't' to terminate upload: "
            ).lower()
            if choice != "c":
                self._print("Upload terminated. Participant list unchanged.")
                return False

        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            self._print(f"Found {len(duplicates)} duplicate name(s):")
            for dup in duplicates:
                self._print(f"  - {dup.name} ({dup.department})")
            choice = self._ask(
                "Enter 'r' to remove duplicates (keep first occurrence), or 't' to terminate upload: "
            ).lower()
            if choice != "r":
                self._print("Upload terminated. Participant list unchanged.")
                return False

        if not valid:
            self._print("No valid participants found. Participant list unchanged.")
            return False

        self.users = valid
        self.list_loaded = True
        self.lottery_manager = None
        self._print(f"Participant list loaded: {len(valid)} participant(s).")
        return True

    def _view_groups(self) -> None:
        if not self.list_loaded:
            self._print("Please load a participant list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("Department groups:")
        for index, (department, count) in enumerate(info.items(), start=1):
            self._print(f"  {index}. {department}: {count} person(s)")
        self._print(f"Total: {len(self.users)} participant(s)")

    # ----------------------------------------------------------- prize config
    def _load_preset_prizes(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                self._print("Error: " + error)
        else:
            self._print("Preset prizes loaded.")

    def _select_avoid_groups(self):
        groups = self._group_names()
        if not groups:
            self._print("No participant list loaded; no avoidance groups available.")
            return []
        self._print("Available department groups:")
        for index, department in enumerate(groups, start=1):
            self._print(f"  {index}. {department}")
        raw = self._ask("Select avoidance group numbers (comma-separated, blank for none): ")
        selected = []
        for token in _split_tokens(raw):
            if token.isdigit() and 1 <= int(token) <= len(groups):
                group = groups[int(token) - 1]
                if group not in selected:
                    selected.append(group)
            else:
                self._print(f"Ignoring invalid group selection: {token}")
        return selected

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_positive_int("Quantity: ")
        avoid_groups = self._select_avoid_groups()
        drawer = self._ask("Associated lottery person (blank for none, e.g. Chen Qixian): ")
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer or None)
        except ValueError as exc:
            self._print(f"Error: {exc}")
            return
        self._print("Prize added.")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        self._print("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            self._print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes to reorder.")
            return
        self._view_prizes()
        raw = self._ask(
            "Enter new order as serial numbers separated by commas (e.g. 2,1,3); blank to keep: "
        )
        if not raw:
            return
        try:
            order = [int(token) for token in _split_tokens(raw)]
        except ValueError:
            self._print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize order updated.")
            self._view_prizes()
        else:
            self._print("Invalid order: each serial number must appear exactly once.")

    # ------------------------------------------------------- lottery process
    def _start_lottery(self) -> None:
        if not self.list_loaded:
            self._print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured. Load presets or add prizes first.")
            return
        if self.result_manager.get_winners():
            confirm = self._ask("Previous lottery results will be cleared. Continue? (y/n): ")
            if confirm.lower() != "y":
                return

        self.result_manager = ResultManager()
        self.lottery_manager = LotteryManager(self.users)
        self._print("")
        self._print("=== Lottery started ===")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)
        self._print("")
        self._print("=== All rounds completed ===")
        self._show_final_results(prizes)

    def _await_command(self) -> str:
        """Wait for the operator's command before the next draw.

        Returns ACTION_DRAW to proceed, or CMD_TERMINATE to end the round.
        """
        while True:
            command = self._ask("[Enter] draw next | 'pause' | 'terminate': ").lower()
            if command in ("", CMD_CONTINUE):
                return ACTION_DRAW
            if command == CMD_TERMINATE:
                return CMD_TERMINATE
            if command == CMD_PAUSE:
                self._print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    resume = self._ask("(paused) ").lower()
                    if resume == CMD_CONTINUE:
                        self._print("Lottery resumed.")
                        return ACTION_DRAW
                    if resume == CMD_TERMINATE:
                        return CMD_TERMINATE
                    self._print("Unknown command. Use 'continue' or 'terminate'.")
            self._print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    def _run_round(self, index: int, total: int, prize) -> None:
        self._print("")
        self._print(f"--- Round {index}/{total}: {prize.name} ---")
        self._print(f"Quantity: {prize.quantity}")
        self._print(f"Rules: {self.lottery_manager.describe_rules(prize)}")

        round_winners = []
        terminated = False
        while len(round_winners) < prize.quantity:
            if self._await_command() == CMD_TERMINATE:
                terminated = True
                break
            position = len(round_winners) + 1
            self._print(f"Currently drawing the {ordinal(position)} winner...")
            winner = self.lottery_manager.draw_one(prize)
            if winner is None:
                self._print("No eligible participants remain for this prize. Round ends early.")
                break
            round_winners.append(winner)
            self.result_manager.add_winner(winner, prize)
            self._print(f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}!")

        self.lottery_manager.end_round(prize, round_winners)

        if terminated:
            self._print(f"Round terminated. {len(round_winners)} of {prize.quantity} winner(s) drawn.")
        self._print(f"Results of round {index}:")
        if round_winners:
            for order, winner in enumerate(round_winners, start=1):
                self._print(f"  {order}. {winner.name} ({winner.department})")
        else:
            self._print("  (no winners)")

    # ---------------------------------------------------------------- results
    def _show_final_results(self, prizes) -> None:
        if not self.result_manager.get_winners():
            self._print("No winners recorded yet.")
            return
        grouped = self.result_manager.get_winners_by_prize(prizes)
        self._print("")
        self._print("=== Winner List ===")
        for prize in prizes:
            winners = grouped.get(prize.name, [])
            self._print(f"{prize.name}:")
            if not winners:
                self._print("  (no winners)")
            for winner in winners:
                self._print(
                    f"  #{winner.winning_order} {winner.user.name} ({winner.user.department})"
                )
        self._print(f"Total winners: {len(self.result_manager.get_winners())}")

    def _show_results(self) -> None:
        self._show_final_results(self.prize_manager.get_prizes())

    def _export_results(self) -> None:
        prizes = self.prize_manager.get_prizes()
        success, message = self.result_manager.export_to_csv(prizes)
        self._print(message)


def main() -> None:
    """Start the interactive lottery system."""
    LotterySystemCLI().run()
