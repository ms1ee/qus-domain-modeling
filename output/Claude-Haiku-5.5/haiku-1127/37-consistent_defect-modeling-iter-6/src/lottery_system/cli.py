"""Command-line interface and lottery process control."""

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

SEPARATOR = "-" * 60


def ordinal(number):
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._print = output_func
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.lottery = None
        self._paused = False
        self._running = True

    # ------------------------------------------------------------------ menus
    def run(self):
        self._print("Welcome to the Team Building Smart Lottery System")
        handlers = {
            "1": self._menu_load_list,
            "2": self._show_groups,
            "3": self._menu_prizes,
            "4": self._menu_reorder,
            "5": self._start_lottery,
            "6": self._menu_results,
            "0": self._exit,
        }
        try:
            while self._running:
                self._show_main_menu()
                choice = self._ask("Select an option: ").strip()
                handler = handlers.get(choice)
                if handler is None:
                    self._print("Invalid option, please try again.")
                    continue
                handler()
        except (EOFError, KeyboardInterrupt):
            self._print("\nExiting the system.")

    def _show_main_menu(self):
        self._print(SEPARATOR)
        self._print("1. Load participant list")
        self._print("2. View department groups")
        self._print("3. Configure prizes")
        self._print("4. Adjust prize order")
        self._print("5. Start lottery")
        self._print("6. View results / export")
        self._print("0. Exit")
        self._print(SEPARATOR)

    def _exit(self):
        self._running = False
        self._print("Goodbye.")

    def _ask(self, prompt):
        return self._input(prompt)

    def _ask_positive_int(self, prompt):
        while True:
            raw = self._ask(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                self._print("Please enter a valid integer.")
                continue
            if value <= 0:
                self._print("Please enter a positive integer.")
                continue
            return value

    # ------------------------------------------------------- list management
    def _menu_load_list(self):
        self._print("1. Built-in default list")
        self._print("2. Upload custom txt list (each line: Name,Department Group)")
        self._print("0. Cancel")
        choice = self._ask("Select a source: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter the path of the txt file: ").strip().strip('"')
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return
        self._finalize_list_load(users, errors)

    def _finalize_list_load(self, users, errors):
        valid_users, duplicates = self.list_manager.validate_users(users)

        if not users and errors:
            self._print("Load failed:")
            for error in errors:
                self._print(f"  {error}")
            return

        if errors:
            self._print("Invalid entries detected:")
            for error in errors:
                self._print(f"  {error}")
        if duplicates:
            self._print("Duplicate names detected (only the first occurrence is kept):")
            for user in duplicates:
                self._print(f"  Duplicate Name: {user.name} ({user.department})")

        if errors or duplicates:
            choice = self._ask(
                "Type 'r' to remove invalid data and keep the rest, "
                "or 't' to terminate the upload: "
            ).strip().lower()
            if choice != "r":
                self._print("Upload terminated. The previous list is unchanged.")
                return

        if not valid_users:
            self._print("No valid participants found. The previous list is unchanged.")
            return

        self.users = valid_users
        self.lottery = None
        self._print(f"Loaded {len(valid_users)} participant(s) from {self.list_manager.source}.")

    def _show_groups(self):
        if not self.users:
            self._print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._print("Department groups:")
        for index, (department, count) in enumerate(sorted(info.items()), start=1):
            self._print(f"  {index}. {department}: {count} member(s)")
        self._print(f"Total: {len(self.users)} participant(s), {len(info)} group(s).")

    # ------------------------------------------------------- prize management
    def _menu_prizes(self):
        while True:
            self._print("Prize configuration:")
            self._print("1. Load preset prizes")
            self._print("2. Add custom prize")
            self._print("3. List prizes")
            self._print("0. Back")
            choice = self._ask("Select an option: ").strip()
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        self._print(f"  {error}")
                else:
                    self._print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "0":
                return
            else:
                self._print("Invalid option, please try again.")

    def _add_custom_prize(self):
        name = self._ask("Prize name: ").strip()
        quantity = self._ask_positive_int("Quantity: ")
        drawer = self._ask("Associated lottery person (optional, Enter to skip): ").strip() or None
        if self.users:
            groups = sorted({user.department for user in self.users})
            self._print("Available department groups: " + ", ".join(groups))
        raw_groups = self._ask("Avoidance groups (comma-separated, Enter for none): ")
        avoid_groups = [group.strip() for group in raw_groups.split(",") if group.strip()]
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            self._print(f"Error: {exc}")
            return
        self._print(f"Prize '{name}' added.")

    def _show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) or "-"
            drawer = prize.associated_drawer or "-"
            self._print(
                f"{index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {avoid}"
            )

    def _menu_reorder(self):
        self._show_prizes()
        if not self.prize_manager.get_prizes():
            return
        raw = self._ask("Enter the new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.split()]
        except ValueError:
            self._print("Invalid input: serial numbers must be integers.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._print("Prize order updated.")
            self._show_prizes()
        else:
            self._print("Invalid order: every serial number must appear exactly once.")

    # ------------------------------------------------------ lottery process
    def _start_lottery(self):
        if not self.users:
            self._print("Please load the participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._print("Please configure prizes first.")
            return
        if self.result_manager.get_all_winners():
            choice = self._ask("Previous results will be cleared. Continue? (y/n): ").strip().lower()
            if choice != "y":
                return
            self.result_manager = ResultManager()

        self.lottery = LotteryManager(self.users)
        self._paused = False
        total = len(prizes)
        self._print(f"Starting lottery: {total} round(s), {len(self.users)} participant(s).")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, total, prize)
            self.lottery.end_round(prize)

        self._print(SEPARATOR)
        self._print("Lottery finished.")
        self._show_summary(prizes)
        choice = self._ask("Export the winner list now? (y/n): ").strip().lower()
        if choice == "y":
            self._export(prizes)

    def _run_round(self, index, total, prize):
        self._print(SEPARATOR)
        self._print(f"Round {index}/{total}: {prize.name}")
        self._print(f"Quantity: {prize.quantity}")
        self._print(f"Rule: {self.lottery.describe_rule(prize)}")
        self._print(SEPARATOR)

        self._paused = False
        round_winners = []
        for position in range(1, prize.quantity + 1):
            command = self._await_draw_command()
            if command == "terminate":
                self._print("Round terminated by operator. Remaining winners are skipped.")
                break
            if not self.lottery.has_eligible(prize):
                self._print("No eligible participants remain for this prize. Round ends.")
                break
            self._print(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                self._print("No eligible participants remain for this prize. Round ends.")
                break
            winner = self.result_manager.add_winner(user, prize)
            round_winners.append(winner)
            self._print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self._print(f"Round {index} results:")
        if not round_winners:
            self._print("  No winners in this round.")
        for winner in round_winners:
            self._print(
                f"  {winner.winning_order}. {winner.name} ({winner.department}) - {winner.prize_name}"
            )

    def _await_draw_command(self):
        """Wait for the operator. Returns 'draw' or 'terminate'."""
        while True:
            if self._paused:
                prompt = "Paused. Type 'continue' to resume or 'terminate' to end this round: "
            else:
                prompt = "Press Enter to draw the next winner, or type 'pause' / 'terminate': "
            command = self._ask(prompt).strip().lower()

            if command == "terminate":
                self._paused = False
                return "terminate"
            if command == "pause":
                if self._paused:
                    self._print("Lottery is already paused.")
                else:
                    self._paused = True
                    self._print("Lottery paused.")
                continue
            if command == "continue":
                if not self._paused:
                    self._print("Lottery is not paused.")
                    continue
                self._paused = False
                self._print("Lottery resumed.")
                return "draw"
            if command == "":
                if self._paused:
                    self._print("Lottery is paused. Type 'continue' to resume.")
                    continue
                return "draw"
            self._print(f"Unknown command '{command}'. Use Enter, 'pause', 'continue' or 'terminate'.")

    # ------------------------------------------------------------- results
    def _menu_results(self):
        prizes = self.prize_manager.get_prizes()
        self._show_summary(prizes)
        if self.result_manager.get_all_winners():
            choice = self._ask("Export the winner list to a txt/CSV file? (y/n): ").strip().lower()
            if choice == "y":
                self._export(prizes)

    def _show_summary(self, prizes):
        if not self.result_manager.get_all_winners():
            self._print("No winners recorded yet.")
            return
        sorted_prizes = sorted(prizes, key=lambda prize: prize.level)
        grouped = self.result_manager.get_winners_by_prize(sorted_prizes)
        self._print("=== Winner List (by prize level, high to low) ===")
        for prize_name, winners in grouped.items():
            if not winners:
                continue
            self._print(f"{prize_name}:")
            for winner in winners:
                self._print(
                    f"  {winner.winning_order}. {winner.name} ({winner.department}) "
                    f"- {winner.win_time:%Y-%m-%d %H:%M:%S}"
                )

    def _export(self, prizes):
        success, message = self.result_manager.export_to_csv(prizes)
        self._print(message)


def main():
    LotteryCLI().run()
