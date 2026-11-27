"""Command-line interface for the team building lottery system."""

from lottery_system.models import User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager

MENU = """
========== Main Menu ==========
1. Load built-in default list
2. Upload custom txt list
3. View department groups
4. Load preset prize library
5. Add custom prize
6. View prize list
7. Reorder prizes
8. Start lottery
9. Export winner list (CSV in .txt)
0. Exit
================================"""


def _ordinal(number: int) -> str:
    """Return an English ordinal such as 1st, 2nd, 3rd, 11th."""
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotterySystemCLI:
    """Interactive menu-driven controller."""

    def __init__(self, input_func=input, output_func=print):
        self._input = input_func
        self._output = output_func
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._lottery: LotteryManager | None = None

    # ------------------------------------------------------------ helpers
    def _say(self, message: str = "") -> None:
        self._output(message)

    def _ask(self, prompt: str) -> str:
        return self._input(prompt)

    def _report_errors(self, errors: list[str]) -> None:
        if not errors:
            return
        self._say("Errors found:")
        for error in errors:
            self._say(f"  - {error}")

    def _report_duplicates(self, duplicates: list[User]) -> None:
        self._say("Duplicate entries:")
        for user in duplicates:
            self._say(f"  - {user.name} ({user.department})")

    def _group_names(self) -> list[str]:
        return list(self._list_manager.get_group_info(self._users).keys())

    # --------------------------------------------------------- main loop
    def run(self) -> None:
        self._say("Welcome to the Company Team Building Smart Lottery System.")
        handlers = {
            "1": self._load_default_list,
            "2": self._upload_custom_list,
            "3": self._show_groups,
            "4": self._load_preset_prizes,
            "5": self._add_custom_prize,
            "6": self._view_prizes,
            "7": self._reorder_prizes,
            "8": self._start_lottery,
            "9": self._export_results,
        }
        while True:
            self._say(MENU)
            choice = self._ask("Select an option: ").strip()
            if choice == "0":
                self._say("Goodbye!")
                return
            handler = handlers.get(choice)
            if handler is None:
                self._say("Invalid option, please try again.")
                continue
            handler()

    # ------------------------------------------------------ list module
    def _load_default_list(self) -> None:
        users, errors = self._list_manager.load_default_list()
        self._report_errors(errors)
        valid, duplicates = self._list_manager.validate_users(users)
        if duplicates:
            self._say("Duplicate entries in built-in list were removed automatically:")
            self._report_duplicates(duplicates)
        if not valid:
            self._say("No valid users in the built-in list.")
            return
        self._users = valid
        self._say(f"Loaded {len(valid)} users from the built-in list.")

    def _upload_custom_list(self) -> None:
        raw = self._ask(
            "Enter the path of the txt file (one 'Name,Department Group' per line): "
        ).strip()
        if not raw:
            self._say("Upload cancelled.")
            return

        users, errors = self._list_manager.load_custom_list(raw)
        if errors:
            self._report_errors(errors)
            answer = self._ask(
                f"{len(errors)} invalid line(s) found. Type 'r' to remove them and continue, "
                "or 't' to terminate the upload: "
            ).strip().lower()
            if answer != "r":
                self._say("Upload terminated. Current list unchanged.")
                return

        valid, duplicates = self._list_manager.validate_users(users)
        if duplicates:
            self._report_duplicates(duplicates)
            answer = self._ask(
                "Duplicate names found. Type 'r' to remove duplicates and continue, "
                "or 't' to terminate the upload: "
            ).strip().lower()
            if answer != "r":
                self._say("Upload terminated. Current list unchanged.")
                return

        if not valid:
            self._say("No valid users remain. Current list unchanged.")
            return
        self._users = valid
        self._say(f"Loaded {len(valid)} users from '{raw}'.")

    def _show_groups(self) -> None:
        if not self._users:
            self._say("No participant list loaded. Please load a list first.")
            return
        info = self._list_manager.get_group_info(self._users)
        self._say("Department groups:")
        for department, count in info.items():
            self._say(f"  {department}: {count} people")
        self._say(f"Total: {len(self._users)} people")

    # ------------------------------------------------------ prize module
    def _load_preset_prizes(self) -> None:
        errors = self._prize_manager.load_default_prizes()
        if errors:
            self._say("Some preset prizes could not be added:")
            for error in errors:
                self._say(f"  - {error}")
        self._say(f"Preset prize library processed. Current prize count: "
                  f"{len(self._prize_manager.get_prizes())}.")

    def _choose_avoid_groups(self) -> list[str]:
        groups = self._group_names()
        if groups:
            self._say("Available department groups:")
            for index, group in enumerate(groups, start=1):
                self._say(f"  {index}. {group}")
        raw = self._ask(
            "Avoidance groups (group numbers or names, comma-separated; blank for none): "
        ).strip()
        if not raw:
            return []
        selected: list[str] = []
        for token in (item.strip() for item in raw.split(",")):
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                selected.append(groups[int(token) - 1])
            else:
                selected.append(token)
        return selected

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ").strip()
        quantity_text = self._ask("Quantity: ").strip()
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be a whole number. Prize not added.")
            return
        drawer = self._ask("Associated lottery person (leave blank for none): ").strip() or None
        avoid_groups = self._choose_avoid_groups()
        try:
            self._prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            self._say(f"Could not add prize: {exc}")
            return
        self._say(f"Prize '{name}' added.")

    def _view_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._say("Prize list (round order):")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            self._say(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Associated person: {drawer} | Avoid groups: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        if not self._prize_manager.get_prizes():
            self._say("No prizes configured.")
            return
        self._view_prizes()
        raw = self._ask("Enter new order as serial numbers, e.g. '2 1 3' (blank to cancel): ")
        tokens = raw.replace(",", " ").split()
        if not tokens:
            self._say("Reorder cancelled.")
            return
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            self._say("Invalid input. Use serial numbers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            self._say("Prize order updated.")
            self._view_prizes()
        else:
            self._say("Invalid order. Include every serial number exactly once.")

    # ---------------------------------------------------- lottery module
    def _on_drawing(self, index: int, total: int) -> None:
        self._say(f"Currently drawing the {_ordinal(index)} winner ({index}/{total})...")

    def _on_winner(self, user: User, prize) -> None:
        self._say(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

    def _start_lottery(self) -> None:
        if not self._users:
            self._say("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            self._say("Please configure prizes first.")
            return
        if self._lottery is None:
            self._lottery = LotteryManager(self._users)

        self._say("Lottery started. During draws you may type 'pause', 'continue' or 'terminate'.")
        total_rounds = len(prizes)
        for round_no, prize in enumerate(prizes, start=1):
            self._say("")
            self._say(f"----- Round {round_no}/{total_rounds}: {prize.name} -----")
            self._say(f"Quantity: {prize.quantity}")
            self._say(f"Rules: {self._lottery.describe_rules(prize)}")

            winners = self._lottery.draw_prize(
                prize,
                read_command=self._ask,
                on_drawing=self._on_drawing,
                on_winner=self._on_winner,
            )

            self._say(f"Round results for {prize.name}:")
            if not winners:
                self._say("  (no winners)")
            for position, user in enumerate(winners, start=1):
                self._say(f"  {position}. {user.name} ({user.department})")
            if len(winners) < prize.quantity:
                self._say(
                    f"Round finished with {len(winners)} of {prize.quantity} winners "
                    "(terminated or no eligible candidates)."
                )

        self._say("")
        self._show_summary()

    def _show_summary(self) -> None:
        if self._lottery is None:
            self._say("No lottery has been run yet.")
            return
        prizes = self._prize_manager.get_prizes()
        grouped = self._lottery.result_manager.get_winners_by_prize(prizes)
        self._say("========== Complete Winner List ==========")
        found = False
        for prize in prizes:
            for winner in grouped.get(prize.name, []):
                found = True
                self._say(
                    f"Name: {winner.user.name} | Department: {winner.user.department} | "
                    f"Prize: {prize.name}"
                )
        if not found:
            self._say("No winners recorded.")
        self._say("==========================================")

    def _export_results(self) -> None:
        if self._lottery is None:
            self._say("No lottery has been run yet. Nothing to export.")
            return
        _, message = self._lottery.result_manager.export_to_csv(
            self._prize_manager.get_prizes()
        )
        self._say(message)


def main() -> None:
    """Start the interactive lottery system."""
    cli = LotterySystemCLI()
    try:
        cli.run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting lottery system.")
