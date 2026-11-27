"""Command-line interface for the lottery system."""

from __future__ import annotations

from .config import DRAW_DELAY_SECONDS
from .console import ConsoleInput
from .models import Prize, User
from .services.list_manager import ListManager
from .services.lottery_manager import LotteryManager
from .services.lottery_runner import LotteryRunner
from .services.prize_manager import PrizeManager
from .services.result_manager import ResultManager

MAIN_MENU = """
----------------------------------------
 1. Load built-in default team building list
 2. Upload custom txt list (Name,Department Group per line)
 3. View department groups and member counts
 4. Prize configuration
 5. Start lottery
 6. Export winner list (CSV txt)
 0. Exit
----------------------------------------"""

PRIZE_MENU = """
 1. View prizes (lottery order)
 2. Load preset prize library
 3. Add custom prize
 4. Reorder prizes
 0. Back"""


class LotterySystemCLI:
    def __init__(self, console: ConsoleInput | None = None,
                 draw_delay: float = DRAW_DELAY_SECONDS) -> None:
        self.console = console if console is not None else ConsoleInput()
        self.draw_delay = draw_delay
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.list_label = "None"
        self.has_results = False

    # ----- helpers -------------------------------------------------------
    def _say(self, message: str = "") -> None:
        print(message)

    def _ask(self, message: str) -> str:
        return self.console.prompt(message).strip()

    # ----- main loop -----------------------------------------------------
    def run(self) -> int:
        self._say("=== Company Team Building Smart Lottery System ===")
        try:
            while True:
                self._say(MAIN_MENU)
                choice = self._ask("Select an option: ")
                if choice == "1":
                    self._load_default_list()
                elif choice == "2":
                    self._load_custom_list()
                elif choice == "3":
                    self._show_groups()
                elif choice == "4":
                    self._manage_prizes()
                elif choice == "5":
                    self._start_lottery()
                elif choice == "6":
                    self._export_results()
                elif choice == "0":
                    break
                else:
                    self._say("Invalid option, please try again.")
        except EOFError:
            self._say("\nInput closed. Exiting.")
        self._say("Goodbye!")
        return 0

    # ----- list management -----------------------------------------------
    def _load_default_list(self) -> None:
        users, errors = self.list_manager.load_default_list()
        self._accept_list(users, errors, "built-in default list")

    def _load_custom_list(self) -> None:
        path = self._ask("Enter the path of the txt list: ").strip('"')
        if not path:
            self._say("No path entered.")
            return
        users, errors = self.list_manager.load_custom_list(path)
        self._accept_list(users, errors, f"custom file '{path}'")

    def _accept_list(self, users: list[User], errors: list[str], label: str) -> None:
        if errors:
            self._say(f"Found {len(errors)} problem(s) in the list:")
            for error in errors:
                self._say(f"  - {error}")
        if not users:
            self._say("No valid participants found. The list was not loaded.")
            return
        if errors:
            answer = self._ask(
                f"Remove the invalid entries and use the {len(users)} valid "
                "participants? [y = remove invalid and continue / "
                "n = terminate upload]: "
            )
            if answer.lower() not in ("y", "yes"):
                self._say("Upload terminated. Previous list kept.")
                return
        self.users = users
        self.list_label = label
        self._say(f"Loaded {len(users)} participants from {label}.")

    def _show_groups(self) -> None:
        if not self.users:
            self._say("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        self._say(f"Valid department groups ({len(info)}):")
        for index, (department, count) in enumerate(sorted(info.items()), start=1):
            self._say(f"  {index}. {department}: {count} member(s)")

    def _group_names(self) -> list[str]:
        return sorted(self.list_manager.get_group_info(self.users).keys())

    # ----- prize configuration -------------------------------------------
    def _manage_prizes(self) -> None:
        while True:
            self._say(PRIZE_MENU)
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    self._say(f"  - {error}")
                self._say("Preset prize library loaded.")
            elif choice == "3":
                self._add_prize()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                self._say("Invalid option, please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            self._say("No prizes configured.")
            return
        self._say("Prizes in lottery order:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            self._say(f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                      f"lottery person: {drawer} | avoid groups: {groups}")

    def _choose_avoid_groups(self) -> list[str] | None:
        groups = self._group_names()
        if groups:
            self._say("Department groups:")
            for index, group in enumerate(groups, start=1):
                self._say(f"  {index}. {group}")
        raw = self._ask("Avoidance groups (numbers or names, comma-separated; "
                        "blank for none): ")
        if not raw:
            return []
        selected: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit():
                index = int(token)
                if not groups or not 1 <= index <= len(groups):
                    self._say(f"Invalid group number: {token}")
                    return None
                selected.append(groups[index - 1])
            else:
                selected.append(token)
        return selected

    def _add_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity_text = self._ask("Quantity: ")
        try:
            quantity = int(quantity_text)
        except ValueError:
            self._say("Quantity must be an integer. Prize not added.")
            return
        drawer = self._ask("Associated lottery person (blank for none): ") or None
        groups = self._choose_avoid_groups()
        if groups is None:
            self._say("Prize not added.")
            return
        try:
            self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            self._say(f"Cannot add prize: {exc}")
            return
        self._say("Prize added.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            self._say("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        raw = self._ask("Enter new order as serial numbers separated by spaces "
                        "(e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            self._say("Invalid input: use integers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            self._say("Prize order updated.")
        else:
            self._say("Invalid order: each serial number must be used exactly once.")

    # ----- lottery -------------------------------------------------------
    def _start_lottery(self) -> None:
        if not self.users:
            self._say("Load a participant list first.")
            return
        prizes: list[Prize] = self.prize_manager.get_prizes()
        if not prizes:
            self._say("Configure at least one prize first.")
            return
        confirm = self._ask("Type 'start' to begin the lottery: ")
        if confirm.lower() != "start":
            self._say("Lottery cancelled.")
            return

        self.result_manager = ResultManager()
        lottery = LotteryManager(self.users)
        runner = LotteryRunner(lottery, self.result_manager, self.console,
                               output=self._say, draw_delay=self.draw_delay)
        runner.run(prizes)
        self.has_results = True
        self._print_summary(prizes)

        answer = self._ask("Export the winner list to a txt file now? [y/n]: ")
        if answer.lower() in ("y", "yes"):
            self._export_results()

    def _print_summary(self, prizes: list[Prize]) -> None:
        self._say("\n===== Complete Winner List =====")
        by_prize = self.result_manager.get_winners_by_prize(prizes)
        for prize in prizes:
            self._say(f"{prize.name}:")
            winners = by_prize.get(prize.name, [])
            if not winners:
                self._say("  (no winners)")
            for winner in winners:
                self._say(f"  {winner.winning_order}. {winner.user.name} "
                          f"({winner.user.department}) - {winner.prize_name}")

    def _export_results(self) -> None:
        if not self.has_results:
            self._say("No lottery results to export yet.")
            return
        _, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        self._say(message)


def main() -> int:
    return LotterySystemCLI().run()
