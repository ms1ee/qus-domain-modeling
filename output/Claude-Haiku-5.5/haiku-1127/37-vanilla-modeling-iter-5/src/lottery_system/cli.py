"""Command-line interaction for the lottery system."""

import re

from .config import LOTTERY_PERSONS
from .models import User
from .services.list_manager import ListManager
from .services.lottery_manager import LotteryManager
from .services.prize_manager import PrizeManager
from .services.result_manager import ResultManager

LINE = "=" * 64
SUB_LINE = "-" * 64


class ExitProgram(Exception):
    """Raised to leave the program gracefully."""


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        raise ExitProgram()


def _read_command(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        # Non-interactive input ended: keep the lottery going to completion.
        return "continue"


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.users: list[User] = []
        self.results: ResultManager | None = None
        self._last_prizes = []
        self.lottery_completed = False

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        print(LINE)
        print("Company Team Building - Smart Lottery System")
        print(LINE)
        try:
            while True:
                self._show_status()
                self._show_main_menu()
                choice = _ask("Select an option: ")
                self._dispatch(choice)
        except (ExitProgram, KeyboardInterrupt):
            print("\nGoodbye!")

    def _show_status(self) -> None:
        print(
            f"\n[Status] Participants: {len(self.users)} | "
            f"Prizes: {len(self.prize_manager.get_prizes())} | "
            f"Lottery completed: {'yes' if self.lottery_completed else 'no'}"
        )

    @staticmethod
    def _show_main_menu() -> None:
        print("\n1. Load participant list")
        print("2. View department groups")
        print("3. Prize configuration")
        print("4. Start lottery")
        print("5. Export results")
        print("0. Exit")

    def _dispatch(self, choice: str) -> None:
        if choice == "1":
            self._list_menu()
        elif choice == "2":
            self._show_groups()
        elif choice == "3":
            self._prize_menu()
        elif choice == "4":
            self._start_lottery()
        elif choice == "5":
            self._export_menu()
        elif choice == "0":
            raise ExitProgram()
        else:
            print("Invalid option, please try again.")

    # ----- list management -----------------------------------------------
    def _list_menu(self) -> None:
        print(f"\n{SUB_LINE}\nParticipant List\n{SUB_LINE}")
        print("1. Load built-in default team building list")
        print("2. Upload custom txt list (each line: Name,Department)")
        print("0. Back")
        choice = _ask("Select an option: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            self._apply_loaded_list(users, errors)
        elif choice == "2":
            path = _ask("Enter txt file path: ").strip('"').strip("'")
            if not path:
                print("Upload cancelled.")
                return
            users, errors = self.list_manager.load_custom_list(path)
            self._apply_loaded_list(users, errors)
        elif choice == "0":
            return
        else:
            print("Invalid option.")

    def _apply_loaded_list(self, users, errors) -> None:
        if not users and not errors:
            print("The list is empty. Nothing was loaded.")
            return

        valid, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate Name: '{user.name}' ({user.department}) already appears earlier in the list"
            for user in duplicates
        )

        if not problems:
            self._commit_list(valid)
            return

        print(f"\nFound {len(problems)} problem(s) in the list:")
        for index, problem in enumerate(problems, start=1):
            print(f"  {index}. {problem}")
        print(f"{len(valid)} valid participant(s) found.")
        print("Options:")
        print("  1. Remove invalid/duplicate data and continue")
        print("  2. Manually remove specific valid participants and continue")
        print("  3. Terminate upload")
        choice = _ask("Select an option: ")

        if choice == "1":
            if not valid:
                print("No valid participants remain. Upload terminated.")
                return
            self._commit_list(valid)
        elif choice == "2":
            if not valid:
                print("No valid participants remain. Upload terminated.")
                return
            self._print_users(valid)
            raw = _ask("Enter numbers to remove (comma separated), or blank to keep all: ")
            to_remove = self._parse_indexes(raw, len(valid))
            kept = [user for index, user in enumerate(valid, start=1) if index not in to_remove]
            if not kept:
                print("No participants would remain. Upload terminated.")
                return
            self._commit_list(kept)
        else:
            print("Upload terminated. The previous list (if any) is kept.")

    def _commit_list(self, users) -> None:
        self.users = list(users)
        if self.list_manager.source_type == "custom":
            source = f"custom file '{self.list_manager.file_path}'"
        else:
            source = "built-in default list"
        print(f"Loaded {len(self.users)} participant(s) from {source}.")

    @staticmethod
    def _parse_indexes(text: str, size: int) -> set[int]:
        result: set[int] = set()
        for token in re.split(r"[\s,]+", text.strip()):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= size:
                result.add(int(token))
            else:
                print(f"Ignoring invalid number: '{token}'")
        return result

    @staticmethod
    def _print_users(users) -> None:
        for index, user in enumerate(users, start=1):
            print(f"  {index}. {user.name} ({user.department})")

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded. Please load a list first.")
            return
        info = self.list_manager.get_group_info(self.users)
        print(f"\n{SUB_LINE}\nDepartment Groups\n{SUB_LINE}")
        for index, (department, count) in enumerate(info.items(), start=1):
            print(f"{index}. {department}: {count} member(s)")
        print(f"Total groups: {len(info)} | Total participants: {len(self.users)}")

    # ----- prize configuration -------------------------------------------
    def _prize_menu(self) -> None:
        while True:
            print(f"\n{SUB_LINE}\nPrize Configuration\n{SUB_LINE}")
            print("1. View prizes")
            print("2. Load preset prize library")
            print("3. Add custom prize")
            print("4. Set avoid groups for a prize")
            print("5. Reorder prizes (lottery sequence)")
            print("0. Back")
            choice = _ask("Select an option: ")
            if choice == "1":
                self._show_prizes()
            elif choice == "2":
                errors = self.prize_manager.load_default_prizes()
                for error in errors:
                    print(error)
                print("Preset prizes loaded.")
            elif choice == "3":
                self._add_custom_prize()
            elif choice == "4":
                self._set_avoid_groups()
            elif choice == "5":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _show_prizes(self):
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return prizes
        print("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"{index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {groups}"
            )
        return prizes

    def _add_custom_prize(self) -> None:
        name = _ask("Prize name: ")
        if not name:
            print("Prize name is required. Cancelled.")
            return
        raw_quantity = _ask("Quantity: ")
        if not raw_quantity.isdigit() or int(raw_quantity) <= 0:
            print("Quantity must be a positive integer. Cancelled.")
            return
        quantity = int(raw_quantity)

        print("Associated lottery person:")
        for index, person in enumerate(LOTTERY_PERSONS, start=1):
            print(f"  {index}. {person}")
        print("  0. None")
        answer = _ask("Select a number, type a name, or leave blank for none: ")
        if answer in ("", "0"):
            drawer = None
        elif answer.isdigit() and 1 <= int(answer) <= len(LOTTERY_PERSONS):
            drawer = LOTTERY_PERSONS[int(answer) - 1]
        else:
            drawer = answer

        groups = self._select_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity {prize.quantity}).")

    def _select_groups(self) -> list[str]:
        available = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        if available:
            print("Department groups:")
            for index, department in enumerate(available, start=1):
                print(f"  {index}. {department}")
        raw = _ask("Enter avoid group numbers or names, comma separated (blank for none): ")
        return self._resolve_groups(raw, available)

    @staticmethod
    def _resolve_groups(raw: str, available: list[str]) -> list[str]:
        groups: list[str] = []
        for token in (part.strip() for part in raw.split(",")):
            if not token:
                continue
            if token.isdigit() and available:
                position = int(token)
                if 1 <= position <= len(available):
                    name = available[position - 1]
                else:
                    print(f"Ignoring invalid group number: {token}")
                    continue
            else:
                name = token
            if name not in groups:
                groups.append(name)
        return groups

    def _set_avoid_groups(self) -> None:
        prizes = self._show_prizes()
        if not prizes:
            return
        answer = _ask("Select prize number: ")
        if not answer.isdigit() or not (1 <= int(answer) <= len(prizes)):
            print("Invalid prize number.")
            return
        prize = prizes[int(answer) - 1]
        groups = self._select_groups()
        if self.prize_manager.update_avoid_groups(prize.name, groups):
            shown = ", ".join(groups) or "None"
            print(f"Avoid groups for '{prize.name}' set to: {shown}")
        else:
            print("Prize not found.")

    def _reorder_prizes(self) -> None:
        prizes = self._show_prizes()
        if len(prizes) < 2:
            print("At least two prizes are needed to reorder.")
            return
        raw = _ask("Enter new order as serial numbers (e.g. 2 1 3): ")
        tokens = [token for token in re.split(r"[\s,]+", raw.strip()) if token]
        if not tokens or not all(token.isdigit() for token in tokens):
            print("Invalid input: please enter serial numbers only.")
            return
        order = [int(token) for token in tokens]
        if self.prize_manager.reorder_prizes(order):
            print("Prize sequence updated.")
        else:
            print("Invalid order: each serial number must be used exactly once.")

    # ----- lottery process -----------------------------------------------
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return

        print(f"\nLottery sequence: {len(prizes)} round(s)")
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} (quantity {prize.quantity})")
        if _ask("Start the lottery now? (y/n): ").lower() not in ("y", "yes"):
            print("Lottery not started.")
            return

        lottery = LotteryManager(self.users)
        results = ResultManager()
        print(f"\n{LINE}")
        print("Lottery started!")
        print("Commands: [Enter] draw next | pause | continue | terminate (end current round)")
        print(LINE)

        for round_index, prize in enumerate(prizes, start=1):
            round_winners = self._run_round(round_index, len(prizes), prize, lottery, results)
            lottery.finish_round(prize, round_winners)

        self.results = results
        self._last_prizes = list(prizes)
        self.lottery_completed = True
        self._print_summary(prizes, results)

        if _ask("Export results to txt now? (y/n): ").lower() in ("y", "yes"):
            self._export(prizes, results)

    def _run_round(self, round_index, total, prize, lottery, results) -> list[User]:
        print(f"\n{SUB_LINE}")
        print(f"Round {round_index}/{total}: {prize.name}")
        print(f"Quantity: {prize.quantity}")
        print(f"Rule: {lottery.describe_rule(prize)}")
        print(SUB_LINE)

        drawn: list[User] = []
        for position in range(1, prize.quantity + 1):
            if not self._await_next_draw():
                print("Round terminated by user; remaining winners of this prize are skipped.")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = lottery.draw_one(prize)
            if user is None:
                print("No eligible participants left for this prize; round ends early.")
                break
            results.add_winner(user, prize)
            drawn.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        print(f"\nRound {round_index} results ({len(drawn)} winner(s), winning order):")
        if not drawn:
            print("  (no winners)")
        for index, user in enumerate(drawn, start=1):
            print(f"  {index}. {user.name} ({user.department})")
        return drawn

    def _await_next_draw(self) -> bool:
        """Handle process control. Returns False when the current round is terminated."""
        while True:
            command = _read_command("Press Enter to draw next (or pause / terminate): ")
            if command in ("", "continue", "draw", "next"):
                return True
            if command == "terminate":
                return False
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    command = _read_command("[paused] > ")
                    if command in ("continue", "resume"):
                        print("Lottery resumed.")
                        return True
                    if command == "terminate":
                        return False
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause' or 'terminate'.")

    @staticmethod
    def _print_summary(prizes, results: ResultManager) -> None:
        ordered_prizes = sorted(prizes, key=lambda prize: prize.level)
        by_prize = results.get_winners_by_prize(ordered_prizes)
        print(f"\n{LINE}")
        print("FINAL WINNER LIST (prize level high to low, then winning order)")
        print(LINE)
        for prize in ordered_prizes:
            winners = by_prize.get(prize.name, [])
            print(f"\n{prize.name} - {len(winners)} winner(s)")
            if not winners:
                print("  (no winners)")
            for index, winner in enumerate(winners, start=1):
                print(f"  {index}. {winner.user.name} ({winner.user.department})")

    # ----- export --------------------------------------------------------
    def _export_menu(self) -> None:
        if self.results is None:
            print("No lottery results yet. Run the lottery first.")
            return
        self._export(self._last_prizes, self.results)

    @staticmethod
    def _export(prizes, results: ResultManager) -> None:
        _, message = results.export_to_csv(prizes)
        print(message)


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
