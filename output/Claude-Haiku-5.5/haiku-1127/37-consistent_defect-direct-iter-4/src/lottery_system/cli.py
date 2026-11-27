"""Command-line interface for the lottery system."""

from __future__ import annotations

from lottery_system.constants import (
    CHEN_QIXIAN,
    CHENG_RU_GROUP,
    JIN_DUO,
    LI_BIN,
    LOTTERY_PERSONS,
    MA_JIAQI,
)
from lottery_system.models import Prize, User, normalize_key
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, prize_level

BANNER = """
==============================================
   Company Team Building Smart Lottery System
==============================================
"""

MENU = """
---------------- Main Menu ----------------
  1. Load participant list
  2. View participant list & department groups
  3. Load default prizes
  4. Add custom prize
  5. View prize configuration
  6. Reorder prizes
  7. Start lottery
  8. Export last results (txt/CSV)
  0. Exit
-------------------------------------------"""


def _ask(prompt: str) -> str:
    return input(prompt).strip()


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _same(a: str | None, b: str) -> bool:
    return normalize_key(a or "") == normalize_key(b)


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self._list_manager = ListManager()
        self._prize_manager = PrizeManager()
        self._users: list[User] = []
        self._results: ResultManager | None = None
        self._last_prizes: list[Prize] = []

    # ------------------------------------------------------------------ main loop
    def run(self) -> None:
        print(BANNER)
        actions = {
            "1": self._load_participants,
            "2": self._show_participants,
            "3": self._load_default_prizes,
            "4": self._add_custom_prize,
            "5": self._view_prizes,
            "6": self._reorder_prizes,
            "7": self._start_lottery,
            "8": self._export_results,
        }
        while True:
            print(MENU)
            choice = _ask("Select an option: ")
            if choice == "0":
                print("Goodbye!")
                return
            action = actions.get(choice)
            if action is None:
                print("Invalid option, please try again.")
                continue
            action()

    # ------------------------------------------------------- list management
    def _load_participants(self) -> None:
        print(
            "\nLoad participant list:\n"
            "  1. Built-in default list\n"
            "  2. Custom txt file (each line: Name,Department)\n"
            "  0. Cancel"
        )
        choice = _ask("Select: ")
        if choice == "1":
            users, errors = self._list_manager.load_default_list()
        elif choice == "2":
            path = _ask("Enter txt file path: ")
            users, errors = self._list_manager.load_custom_list(path)
        else:
            return

        valid, duplicates = self._list_manager.validate_users(users)
        if errors or duplicates:
            print("\nValidation issues found:")
            for error in errors:
                print(f"  - {error}")
            for duplicate in duplicates:
                print(f"  - Duplicate name: {duplicate.name} ({duplicate.department})")
            print(
                f"Total: {len(errors)} format error(s), "
                f"{len(duplicates)} duplicate(s)."
            )
            print(
                "  1. Remove invalid/duplicate entries and continue\n"
                "  2. Terminate upload (keep current list)"
            )
            if _ask("Select: ") != "1":
                print("Upload terminated. Participant list unchanged.")
                return

        if not valid:
            print("No valid participants found. Participant list unchanged.")
            return
        self._users = valid
        print(f"Loaded {len(valid)} participant(s).")

    def _show_participants(self) -> None:
        if not self._users:
            print("No participant list loaded.")
            return
        print(f"\nTotal participants: {len(self._users)}")
        print("Department groups:")
        for department, count in self._list_manager.get_group_info(self._users).items():
            print(f"  - {department}: {count} person(s)")

    # ------------------------------------------------------- prize management
    def _load_default_prizes(self) -> None:
        errors = self._prize_manager.load_default_prizes()
        for error in errors:
            print(error)
        if not errors:
            print("Default prizes loaded.")

    def _add_custom_prize(self) -> None:
        name = _ask("Prize name: ")
        quantity = self._ask_positive_int("Quantity: ")
        groups = self._choose_avoid_groups()
        drawer = self._choose_drawer()
        try:
            self._prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize '{name}' added to position {len(self._prize_manager.get_prizes())}.")

    @staticmethod
    def _ask_positive_int(prompt: str) -> int:
        while True:
            raw = _ask(prompt)
            if raw.isdigit() and int(raw) > 0:
                return int(raw)
            print("Please enter a positive integer.")

    def _choose_avoid_groups(self) -> list[str]:
        groups = list(self._list_manager.get_group_info(self._users).keys()) if self._users else []
        if groups:
            print("Available department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        raw = _ask("Avoidance groups (numbers or names, comma-separated; blank for none): ")
        if not raw:
            return []
        selected: list[str] = []
        for token in (part.strip() for part in raw.split(",")):
            if not token:
                continue
            if token.isdigit() and groups and 1 <= int(token) <= len(groups):
                selected.append(groups[int(token) - 1])
            else:
                selected.append(token)
        return selected

    def _choose_drawer(self) -> str | None:
        print("Associated lottery person:")
        for index, person in enumerate(LOTTERY_PERSONS, start=1):
            print(f"  {index}. {person}")
        print("  0. None")
        raw = _ask("Select: ")
        if raw in ("", "0"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(LOTTERY_PERSONS):
            return LOTTERY_PERSONS[int(raw) - 1]
        for person in LOTTERY_PERSONS:
            if _same(raw, person):
                return person
        print("Invalid selection; no lottery person assigned.")
        return None

    def _view_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoidance groups: {groups} | Lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._view_prizes()
        raw = _ask("Enter new order as serial numbers, e.g. '3 1 2': ")
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            print("Invalid input: please enter numbers only.")
            return
        if self._prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: each serial number must appear exactly once.")

    # ---------------------------------------------------------- lottery flow
    def _start_lottery(self) -> None:
        if not self._users:
            print("Please load a participant list first.")
            return
        prizes = self._prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured. Load default prizes or add custom prizes first.")
            return

        lottery = LotteryManager(self._users)
        results = ResultManager()
        self._results = results
        self._last_prizes = prizes

        print("\nLottery started!")
        print("Commands: Enter = draw next winner, 'pause' = pause, "
              "'terminate' = end current round.")
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize, lottery, results)

        print("\nAll rounds completed.")
        self._show_summary(prizes, results)
        if _ask("Export results now? (y/n): ").lower() == "y":
            self._export_results()

    def _run_round(
        self,
        index: int,
        total: int,
        prize: Prize,
        lottery: LotteryManager,
        results: ResultManager,
    ) -> None:
        print("\n" + "=" * 60)
        print(f"Round {index}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {self._describe_rule(prize)}")
        print("=" * 60)

        lottery.start_round(prize)
        terminated = False
        for position in range(1, prize.quantity + 1):
            print(f"Currently drawing the {_ordinal(position)} winner...")
            if not self._await_command():
                terminated = True
                break
            user = lottery.draw_next()
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            results.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        round_winners = lottery.end_round()
        if terminated:
            print("Round terminated by operator.")
        print(f"Round finished: {len(round_winners)}/{prize.quantity} winner(s) drawn.")

    @staticmethod
    def _await_command() -> bool:
        """Handle operator commands before a draw. Returns False to terminate."""
        while True:
            command = _ask("Press Enter to draw (or type pause / terminate): ").lower()
            if command in ("", "continue"):
                return True
            if command == "terminate":
                return False
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    command = _ask("(paused) > ").lower()
                    if command == "continue":
                        print("Lottery resumed.")
                        return True
                    if command == "terminate":
                        return False
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    @staticmethod
    def _describe_rule(prize: Prize) -> str:
        drawer = prize.associated_drawer
        if _same(drawer, LI_BIN):
            parts = [
                "Only previous winners are excluded "
                "(Li Bin rule: avoidance groups do not apply)."
            ]
        else:
            parts = ["Previous winners are excluded."]
            if prize.avoid_groups:
                parts.append(
                    "Members of avoidance group(s) "
                    f"{', '.join(prize.avoid_groups)} are drawn after other members."
                )
        if drawer:
            parts.append(f"Lottery person: {drawer}.")
        if _same(drawer, MA_JIAQI):
            parts.append(
                "Cheng Ru protection: if neither of the last two "
                f"{CHEN_QIXIAN}/{JIN_DUO} rounds produced a {CHENG_RU_GROUP} winner, "
                f"only {CHENG_RU_GROUP} members are eligible."
            )
        return " ".join(parts)

    def _show_summary(self, prizes: list[Prize], results: ResultManager) -> None:
        print("\n==================== Final Winner List ====================")
        by_prize = results.get_winners_by_prize(prizes)
        for prize in sorted(prizes, key=lambda p: prize_level(p.name)):
            winners = by_prize.get(prize.name, [])
            print(f"\n{prize.name} ({len(winners)}/{prize.quantity})")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(f"  {winner.user.name} - {winner.user.department}")

    # ------------------------------------------------------------- export
    def _export_results(self) -> None:
        if self._results is None:
            print("No lottery results yet.")
            return
        _, message = self._results.export_to_csv(self._last_prizes)
        print(message)


def main() -> None:
    """Program entry point."""
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
