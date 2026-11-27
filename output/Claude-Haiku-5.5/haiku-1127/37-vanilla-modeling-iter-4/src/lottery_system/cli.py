"""Command-line interaction: setup menus, lottery process control and result display."""

from __future__ import annotations

from lottery_system.constants import (
    CHENG_RU_GROUP,
    DEFAULT_DRAW_INTERVAL,
    DEFAULT_EVENT_NAME,
    DRAWER_OPTIONS,
)
from lottery_system.console_input import ConsoleReader
from lottery_system.models import LotterySession, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

COMMAND_HELP = "Commands during a round: pause | continue | terminate"


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryApp:
    """Interactive controller for the whole lottery process."""

    def __init__(self, reader: ConsoleReader | None = None, draw_interval: float = DEFAULT_DRAW_INTERVAL) -> None:
        self._reader = reader if reader is not None else ConsoleReader()
        self._draw_interval = draw_interval
        self._session = LotterySession(event_name=DEFAULT_EVENT_NAME)
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._result_manager = ResultManager()
        self._lottery_manager: LotteryManager | None = None
        self._completed_prizes: list[Prize] = []
        self._lottery_done = False

    # ------------------------------------------------------------------ #
    # Top level
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        try:
            print("=" * 60)
            print(" Company Team Building - Smart Lottery System")
            print("=" * 60)
            name = self._ask(f"Enter event name (blank for '{DEFAULT_EVENT_NAME}'): ")
            if name:
                self._session.event_name = name
            if not self._setup_participants():
                print("No participant list loaded. Exiting.")
                return 0
            self._main_menu()
        except EOFError:
            print("\nInput closed. Exiting.")
        print("Goodbye!")
        return 0

    def _ask(self, message: str) -> str:
        return self._reader.prompt(message).strip()

    def _ask_int(self, message: str) -> int:
        while True:
            raw = self._ask(message)
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            print("Please enter a positive integer.")

    # ------------------------------------------------------------------ #
    # Participant list
    # ------------------------------------------------------------------ #
    def _setup_participants(self) -> bool:
        while True:
            print("\n----- Load participant list -----")
            print("1. Use built-in default team building list")
            print("2. Upload custom txt list (format: Name,Department Group per line)")
            print("q. Quit")
            choice = self._ask("Select an option: ").lower()
            if choice == "1":
                users, errors = self._list_manager.load_default_list()
                if self._accept_users(users, errors):
                    return True
            elif choice == "2":
                path = self._ask("Enter txt file path (or 'b' to go back): ").strip('"').strip()
                if path.lower() == "b":
                    continue
                users, errors = self._list_manager.load_custom_list(path)
                if self._accept_users(users, errors):
                    return True
            elif choice in ("q", "quit", "exit"):
                return False
            else:
                print("Invalid option.")

    def _accept_users(self, users: list[User], errors: list[str]) -> bool:
        valid, duplicates = self._list_manager.validate_users(users)
        if not errors and not duplicates:
            self._commit_users(valid)
            return True

        print("\nValidation issues found:")
        for error in errors:
            print(f"  {error}")
        for duplicate in duplicates:
            print(f"  Duplicate Name: {duplicate.name} ({duplicate.department})")
        print(f"Valid entries: {len(valid)} | Format errors: {len(errors)} | Duplicates: {len(duplicates)}")

        choice = self._ask(
            "Enter 'r' to remove invalid/duplicate entries and continue, or 't' to terminate this upload: "
        ).lower()
        if choice == "r":
            if not valid:
                print("No valid participants remain. Upload terminated.")
                return False
            self._commit_users(valid)
            return True
        print("Upload terminated.")
        return False

    def _commit_users(self, users: list[User]) -> None:
        self._users = list(users)
        self._session.status = "PARTICIPANTS_LOADED"
        print(f"Loaded {len(self._users)} valid participant(s).")

    # ------------------------------------------------------------------ #
    # Main menu
    # ------------------------------------------------------------------ #
    def _main_menu(self) -> None:
        while True:
            print(f"\n===== {self._session.event_name} | Main Menu =====")
            print("1. View department groups")
            print("2. Configure prizes")
            print("3. Start lottery")
            print("4. Export winner list")
            print("q. Quit")
            choice = self._ask("Select: ").lower()
            if choice == "1":
                self._show_groups()
            elif choice == "2":
                self._prize_menu()
            elif choice == "3":
                self._start_lottery()
            elif choice == "4":
                self._export()
            elif choice in ("q", "quit", "exit"):
                return
            else:
                print("Invalid option.")

    def _show_groups(self) -> None:
        if not self._users:
            print("No participants loaded.")
            return
        info = self._list_manager.get_group_info(self._users)
        print("Department groups:")
        for department, count in info.items():
            print(f"  {department}: {count} member(s)")
        print(f"Total participants: {len(self._users)}")

    # ------------------------------------------------------------------ #
    # Prize configuration
    # ------------------------------------------------------------------ #
    def _prize_menu(self) -> None:
        while True:
            print("\n----- Prize configuration -----")
            print("1. Load preset prizes")
            print("2. Add custom prize")
            print("3. Show prizes")
            print("4. Set avoidance groups for a prize")
            print("5. Reorder lottery sequence")
            print("b. Back")
            choice = self._ask("Select: ").lower()
            if choice == "1":
                errors = self._prize_manager.load_default_prizes()
                for error in errors:
                    print(f"  {error}")
                if not errors:
                    print("Preset prizes loaded.")
                self._show_prizes()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._show_prizes()
            elif choice == "4":
                self._set_avoid_groups()
            elif choice == "5":
                self._reorder_prizes()
            elif choice in ("b", "back"):
                return
            else:
                print("Invalid option.")

    def _show_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Current lottery sequence:")
        for index, prize in enumerate(prizes, start=1):
            drawer = prize.associated_drawer or "None"
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            print(
                f"  {index}. {prize.name} | quantity: {prize.quantity} | "
                f"lottery person: {drawer} | avoid groups: {avoid}"
            )

    def _show_groups_brief(self) -> list[str]:
        if not self._users:
            return []
        return list(self._list_manager.get_group_info(self._users).keys())

    def _ask_groups(self) -> list[str]:
        known = self._show_groups_brief()
        if known:
            print("Available department groups: " + "; ".join(known))
        raw = self._ask("Avoidance groups (comma-separated, blank for none): ")
        groups = [group.strip() for group in raw.split(",") if group.strip()]
        known_keys = {group.casefold() for group in known}
        for group in groups:
            if known and group.casefold() not in known_keys:
                print(f"  Warning: group '{group}' is not among current participants (kept as configured).")
        return groups

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        quantity = self._ask_int("Prize quantity: ")

        print("Associated lottery person:")
        print("  0. None")
        for index, drawer in enumerate(DRAWER_OPTIONS, start=1):
            print(f"  {index}. {drawer}")
        drawer: str | None = None
        while True:
            raw = self._ask("Select lottery person (0-{}): ".format(len(DRAWER_OPTIONS)))
            if raw.isdigit() and 0 <= int(raw) <= len(DRAWER_OPTIONS):
                selected = int(raw)
                drawer = None if selected == 0 else DRAWER_OPTIONS[selected - 1]
                break
            print("Invalid selection.")

        groups = self._ask_groups()
        try:
            self._prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize '{name.strip()}' added.")
        except ValueError as exc:
            print(f"Error: {exc}")

    def _set_avoid_groups(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        raw = self._ask("Select prize number: ")
        if not raw.isdigit() or not (1 <= int(raw) <= len(prizes)):
            print("Invalid prize number.")
            return
        groups = self._ask_groups()
        if self._prize_manager.set_avoid_groups(int(raw) - 1, groups):
            print("Avoidance groups updated.")
            self._show_prizes()

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to reorder.")
            return
        self._show_prizes()
        raw = self._ask("Enter new order as serial numbers separated by spaces (e.g. 2 1 3): ")
        try:
            order = [int(token) for token in raw.replace(",", " ").split()]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._show_prizes()
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ------------------------------------------------------------------ #
    # Lottery process
    # ------------------------------------------------------------------ #
    def _start_lottery(self) -> None:
        if self._lottery_done:
            print("The lottery has already been completed in this session.")
            return
        if not self._users:
            print("No participants loaded.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Please configure prizes first.")
            return

        self._lottery_manager = LotteryManager(self._users)
        self._result_manager = ResultManager()
        self._session.status = "RUNNING"
        print(f"\nLottery starts with {len(prizes)} round(s). {COMMAND_HELP}")

        for number, prize in enumerate(prizes, start=1):
            self._run_round(number, len(prizes), prize)

        self._completed_prizes = prizes
        self._lottery_done = True
        self._session.status = "COMPLETED"
        self._print_final_summary(prizes)

    def _run_round(self, number: int, total: int, prize: Prize) -> list[User]:
        assert self._lottery_manager is not None
        print(f"\n----- Round {number}/{total}: {prize.name} -----")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._lottery_manager.describe_rule(prize)}")

        drawn: list[User] = []
        paused = False
        while len(drawn) < prize.quantity:
            command = self._reader.read(timeout=None if paused else self._draw_interval)
            if command is not None:
                paused, stop = self._handle_command(command, paused, len(drawn), prize)
                if stop:
                    break
                continue

            if paused:
                continue

            print(f"Currently drawing the {_ordinal(len(drawn) + 1)} winner...")
            user = self._lottery_manager.draw_one(prize)
            if user is None:
                print("No eligible participants remain for this prize. Round ends.")
                break
            drawn.append(user)
            self._result_manager.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        self._lottery_manager.record_round_result(prize, drawn)

        if drawn:
            print("Round results (winning order):")
            for index, user in enumerate(drawn, start=1):
                print(f"  {index}. {user.name} ({user.department})")
        else:
            print("No winners in this round.")
        return drawn

    def _handle_command(self, command: str, paused: bool, drawn_count: int, prize: Prize) -> tuple[bool, bool]:
        """Return (paused, stop_round)."""
        word = command.strip().lower()
        if word == "":
            return paused, False
        if word == "pause":
            if paused:
                print("Lottery is already paused.")
            else:
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
            return True, False
        if word == "continue":
            if paused:
                print("Lottery resumed.")
            else:
                print("Lottery is not paused.")
            return False, False
        if word == "terminate":
            print(f"Round terminated early after {drawn_count}/{prize.quantity} winner(s).")
            return paused, True
        print(f"Unknown command '{command}'. {COMMAND_HELP}")
        return paused, False

    def _print_final_summary(self, prizes: list[Prize]) -> None:
        print("\n===== Final Winner List =====")
        by_prize = self._result_manager.get_winners_by_prize(prizes)
        ordered = sorted(enumerate(prizes), key=lambda item: (item[1].level, item[0]))
        for _, prize in ordered:
            print(f"\n[{prize.name}]")
            winners = by_prize.get(prize.name, [])
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.winning_order:>3}. {winner.user.name} ({winner.user.department})")

    def _export(self) -> None:
        if not self._lottery_done:
            print("No lottery results to export yet.")
            return
        _, message = self._result_manager.export_to_csv(self._completed_prizes)
        print(message)


__all__ = ["LotteryApp", "CHENG_RU_GROUP"]
