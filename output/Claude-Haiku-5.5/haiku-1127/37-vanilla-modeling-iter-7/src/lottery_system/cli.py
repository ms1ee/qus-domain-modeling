"""Command-line interface for the lottery process."""

from __future__ import annotations

from lottery_system.config import LI_BIN, LOTTERY_DRAWERS, MA_JIAQI
from lottery_system.models import Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(number: int) -> str:
    """Return an English ordinal, e.g. 1 -> '1st'."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def parse_numbers(text: str) -> list[int] | None:
    """Parse whitespace/comma separated integers. Returns None if invalid."""
    tokens = text.replace(",", " ").split()
    if not tokens:
        return None
    try:
        return [int(token) for token in tokens]
    except ValueError:
        return None


def describe_rule(prize: Prize) -> str:
    """Human readable rule description for a prize round."""
    parts: list[str] = []
    drawer = prize.associated_drawer
    if drawer == LI_BIN:
        parts.append(
            "Only previous winners are excluded; avoidance groups are NOT applied (Li Bin rule)."
        )
    else:
        parts.append("Previous winners are excluded.")
        if prize.avoid_groups:
            parts.append(f"Members of avoided groups are excluded: {', '.join(prize.avoid_groups)}.")
    if drawer == MA_JIAQI:
        parts.append(
            "Fallback rule: if the last two Chen Qixian/Jin Duo draws both had no Cheng Ru Group "
            "member, only Cheng Ru Group members are eligible (overrides avoidance groups)."
        )
    return " ".join(parts)


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    # ----- main loop -----------------------------------------------------
    def run(self) -> None:
        print("=" * 60)
        print("  Company Team Building - Smart Lottery System")
        print("=" * 60)
        while True:
            print("\nMain Menu:")
            print("  1. Load participant list")
            print("  2. View department groups")
            print("  3. Configure prizes")
            print("  4. Start lottery")
            print("  0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._menu_load_list()
            elif choice == "2":
                self._view_groups()
            elif choice == "3":
                self._menu_prizes()
            elif choice == "4":
                self._start_lottery()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    # ----- list management -----------------------------------------------
    def _menu_load_list(self) -> None:
        print("\nLoad participant list:")
        print("  1. Built-in default team building list")
        print("  2. Upload custom txt list (format: Name,Department Group per line)")
        print("  0. Back")
        choice = self._ask("Select an option: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return

        reviewed = self._review_list(users, errors)
        if reviewed is None:
            print("List upload terminated. Current list unchanged.")
            return
        self.users = reviewed
        print(f"Loaded {len(self.users)} valid participants.")
        self._view_groups()

    def _review_list(self, users: list[User], errors: list[str]) -> list[User] | None:
        valid, duplicates = self.list_manager.validate_users(users)
        problems = list(errors)
        problems.extend(
            f"Duplicate Name: '{user.name}' ({user.department}) - duplicate entry"
            for user in duplicates
        )
        if not problems:
            return valid

        print("\nData validation found problems:")
        for problem in problems:
            print(f"  - {problem}")
        print(f"Valid entries: {len(valid)}, invalid entries: {len(problems)}")

        while True:
            choice = self._ask(
                f"Enter 'r' to remove invalid data and keep {len(valid)} valid entries, "
                "or 't' to terminate upload: "
            ).lower()
            if choice == "r":
                if not valid:
                    print("No valid entries remain.")
                    return None
                return valid
            if choice == "t":
                return None
            print("Please enter 'r' or 't'.")

    def _view_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nValid department groups:")
        for group, count in info.items():
            print(f"  - {group}: {count} people")
        print(f"Total: {len(self.users)} people in {len(info)} groups")

    # ----- prize management ----------------------------------------------
    def _menu_prizes(self) -> None:
        while True:
            print("\nPrize Configuration:")
            print("  1. Load preset prize library")
            print("  2. Add custom prize")
            print("  3. View prizes")
            print("  4. Reorder lottery sequence")
            print("  0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("Default prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._view_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _select_avoid_groups(self) -> list[str]:
        if not self.users:
            print("No participant list loaded; no avoidance groups can be selected.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        print("Available department groups:")
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        while True:
            text = self._ask("Enter group numbers to avoid, comma separated (blank for none): ")
            if not text:
                return []
            numbers = parse_numbers(text)
            if numbers and all(1 <= number <= len(groups) for number in numbers):
                return [groups[number - 1] for number in dict.fromkeys(numbers)]
            print("Invalid selection, please try again.")

    def _select_drawer(self) -> str | None:
        print("Associated lottery person:")
        print("  0. None")
        for index, drawer in enumerate(LOTTERY_DRAWERS, start=1):
            print(f"  {index}. {drawer}")
        while True:
            text = self._ask("Select lottery person: ")
            if text.isdigit():
                number = int(text)
                if number == 0:
                    return None
                if 1 <= number <= len(LOTTERY_DRAWERS):
                    return LOTTERY_DRAWERS[number - 1]
            print("Invalid selection, please try again.")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name (blank to cancel): ")
        if not name:
            return
        quantity: int | None = None
        while quantity is None:
            text = self._ask("Prize quantity (blank to cancel): ")
            if not text:
                return
            if text.isdigit() and int(text) >= 1:
                quantity = int(text)
            else:
                print("Quantity must be a positive integer.")
        avoid_groups = self._select_avoid_groups()
        drawer = self._select_drawer()
        try:
            self.prize_manager.add_prize(name, quantity, avoid_groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize added: {name} (quantity {quantity}).")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize sequence:")
        for index, prize in enumerate(prizes, start=1):
            avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Lottery person: {drawer} | Avoid groups: {avoid}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if len(prizes) < 2:
            print("At least two prizes are required to reorder.")
            return
        self._view_prizes()
        while True:
            text = self._ask("Enter new order as serial numbers (e.g. 2 1 3), blank to cancel: ")
            if not text:
                return
            order = parse_numbers(text)
            if order and self.prize_manager.reorder_prizes(order):
                print("Lottery sequence updated.")
                self._view_prizes()
                return
            print("Invalid order: use each serial number exactly once.")

    # ----- lottery process -----------------------------------------------
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return

        lottery = LotteryManager(self.users)
        self.result_manager = ResultManager()
        print("\n*** Lottery started ***")
        for round_number, prize in enumerate(prizes, start=1):
            self._run_round(round_number, prize, lottery, self.result_manager)
        print("\n*** All rounds completed ***")
        self._show_summary(prizes)

    def _run_round(
        self,
        round_number: int,
        prize: Prize,
        lottery: LotteryManager,
        results: ResultManager,
    ) -> list[User]:
        drawer = prize.associated_drawer or "None"
        print(f"\n=== Round {round_number}: {prize.name} ===")
        print(f"Quantity: {prize.quantity} | Lottery person: {drawer}")
        print(f"Rule: {describe_rule(prize)}")
        if prize.associated_drawer == MA_JIAQI and lottery.is_fallback_active():
            print("Fallback mechanism ACTIVE: only Cheng Ru Group members are eligible this round.")

        round_winners: list[User] = []
        paused = False
        while len(round_winners) < prize.quantity:
            if paused:
                prompt = "[PAUSED] Type 'continue' to resume or 'terminate' to end this round: "
            else:
                prompt = "Press Enter to draw, or type 'pause' / 'terminate': "
            command = self._ask(prompt).lower()

            if command == "terminate":
                print("Current round terminated and skipped.")
                break
            if command == "pause":
                if paused:
                    print("Lottery is already paused.")
                else:
                    paused = True
                    print("Lottery paused. Type 'continue' to resume.")
                continue
            if command == "continue":
                if paused:
                    paused = False
                    print("Lottery resumed.")
                else:
                    print("Lottery is not paused.")
                continue
            if paused:
                print("Lottery is paused. Type 'continue' to resume or 'terminate' to skip.")
                continue
            if command not in ("", "draw"):
                print("Unknown command.")
                continue

            position = len(round_winners) + 1
            print(f"Currently drawing the {ordinal(position)} winner...")
            winner = lottery.draw_one(prize)
            if winner is None:
                print("No eligible candidates remain for this prize. Round ends early.")
                break
            results.add_winner(winner, prize)
            round_winners.append(winner)
            print(
                f"Congratulations {winner.name} ({winner.department}) for winning {prize.name}!"
            )

        lottery.complete_round(prize, round_winners)
        print(f"Round {round_number} finished: {len(round_winners)} winner(s).")
        for index, winner in enumerate(round_winners, start=1):
            print(f"  {index}. {winner.name} ({winner.department})")
        return round_winners

    def _show_summary(self, prizes: list[Prize]) -> None:
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n=== Complete Winner List (by prize level, then winning order) ===")
        for prize in sorted(prizes, key=lambda item: item.level):
            print(f"\n{prize.name}:")
            winners = grouped.get(prize.name, [])
            if not winners:
                print("  (no winners)")
            for winner in winners:
                print(
                    f"  {winner.winning_order}. {winner.user.name} ({winner.user.department})"
                )

        answer = self._ask("\nExport winner list to txt file? (y/n): ").lower()
        if answer in ("y", "yes"):
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)


def main() -> None:
    """Entry point for the interactive program."""
    cli = LotteryCLI()
    try:
        cli.run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting lottery system.")
