"""Command-line interface for the lottery process."""

from __future__ import annotations

from lottery_system.models import LOTTERY_PERSONS, MA_JIAQI, Prize, User
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ------------------------------------------------------------------ #
    # Input helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    def _confirm(self, prompt: str) -> bool:
        return self._ask(prompt + " (y/n): ").lower() in ("y", "yes")

    @staticmethod
    def _parse_int_list(text: str) -> list[int] | None:
        try:
            return [int(token) for token in text.replace(",", " ").split()]
        except ValueError:
            return None

    # ------------------------------------------------------------------ #
    # Main menu
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        try:
            self._main_menu()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting the lottery system.")

    def _main_menu(self) -> None:
        while True:
            print("\n========== Team Building Smart Lottery ==========")
            print("1. Participant list (load / view groups)")
            print("2. Prize configuration")
            print("3. Start lottery")
            print("4. Show winners")
            print("5. Export winners to txt (CSV)")
            print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                self._list_menu()
            elif choice == "2":
                self._prize_menu()
            elif choice == "3":
                self._start_lottery()
            elif choice == "4":
                self._show_winners()
            elif choice == "5":
                self._export()
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Invalid option, please try again.")

    # ------------------------------------------------------------------ #
    # List management
    # ------------------------------------------------------------------ #
    def _list_menu(self) -> None:
        print("\n--- Participant List ---")
        print("1. Load built-in default list")
        print("2. Upload custom txt list (format: Name,Department Group per line)")
        print("3. View current valid group list and member counts")
        print("0. Back")
        choice = self._ask("Select an option: ")
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
            self._process_loaded_list(users, errors)
        elif choice == "2":
            path = self._ask("Enter txt file path: ")
            users, errors = self.list_manager.load_custom_list(path)
            self._process_loaded_list(users, errors)
        elif choice == "3":
            self._show_groups()

    def _process_loaded_list(self, users: list[User], errors: list[str]) -> None:
        if errors:
            print(f"\nFound {len(errors)} invalid line(s):")
            for error in errors:
                print(f"  - {error}")
            if not self._confirm("Remove invalid data and continue"):
                print("List upload terminated.")
                return

        valid_users, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate name(s):")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
            if not self._confirm("Remove duplicate entries (keep first occurrence) and continue"):
                print("List upload terminated.")
                return

        if not valid_users:
            print("No valid participants found. List not loaded.")
            return

        self.users = valid_users
        # A new participant list starts a fresh event session.
        self.result_manager = ResultManager()
        self.lottery = None
        print(f"\nLoaded {len(self.users)} participant(s).")
        self._show_groups()

    def _show_groups(self) -> None:
        if not self.users:
            print("No participant list loaded.")
            return
        info = self.list_manager.get_group_info(self.users)
        print("\nCurrent department groups:")
        for index, (group, count) in enumerate(info.items(), start=1):
            print(f"  {index}. {group}: {count} member(s)")

    # ------------------------------------------------------------------ #
    # Prize configuration
    # ------------------------------------------------------------------ #
    def _prize_menu(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Reorder lottery sequence")
            print("5. View prizes")
            print("0. Back")
            choice = self._ask("Select an option: ")
            if choice == "1":
                for error in self.prize_manager.load_default_prizes():
                    print(error)
                self._show_prizes()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._show_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("\nPrize sequence:")
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name} | Quantity: {prize.quantity}")
            print(f"     Rule: {prize.rule_description()}")

    def _select_groups(self) -> list[str]:
        """Let the operator select multiple department groups by number."""
        if not self.users:
            print("No participant list loaded; no groups available.")
            return []
        groups = list(self.list_manager.get_group_info(self.users).keys())
        for index, group in enumerate(groups, start=1):
            print(f"  {index}. {group}")
        while True:
            text = self._ask("Select avoidance groups by number (e.g. 1,3), blank for none: ")
            if not text:
                return []
            numbers = self._parse_int_list(text)
            if numbers and all(1 <= number <= len(groups) for number in numbers):
                return [groups[number - 1] for number in dict.fromkeys(numbers)]
            print("Invalid selection, please try again.")

    def _select_drawer(self) -> str | None:
        print("Associated lottery person:")
        for index, person in enumerate(LOTTERY_PERSONS, start=1):
            print(f"  {index}. {person}")
        text = self._ask("Select by number or type a name (blank for none): ")
        if not text:
            return None
        if text.isdigit() and 1 <= int(text) <= len(LOTTERY_PERSONS):
            return LOTTERY_PERSONS[int(text) - 1]
        return text

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        while True:
            text = self._ask("Quantity: ")
            if text.isdigit() and int(text) > 0:
                quantity = int(text)
                break
            print("Quantity must be a positive integer.")
        drawer = self._select_drawer()
        print("Avoidance groups (prize will not be given to members of these groups):")
        groups = self._select_groups()
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
        except ValueError as exc:
            print(f"Prize not added: {exc}")
            return
        print(f"Prize added: {prize.name}")

    def _set_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        for index, prize in enumerate(prizes, start=1):
            print(f"  {index}. {prize.name}")
        text = self._ask("Select prize number: ")
        if not text.isdigit() or not 1 <= int(text) <= len(prizes):
            print("Invalid prize number.")
            return
        prize = prizes[int(text) - 1]
        prize.avoid_groups = self._select_groups()
        print(f"Avoidance groups updated for {prize.name}.")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask("Enter new sequence as serial numbers (e.g. 2 1 3): ")
        order = self._parse_int_list(text)
        if order is None or not self.prize_manager.reorder_prizes(order):
            print("Invalid sequence. Each serial number must appear exactly once.")
            return
        print("Lottery sequence updated.")
        self._show_prizes()

    # ------------------------------------------------------------------ #
    # Lottery process
    # ------------------------------------------------------------------ #
    def _start_lottery(self) -> None:
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure prizes first.")
            return
        if self.lottery is not None:
            print("Lottery already completed in this session. Use option 4 to view results.")
            return

        self.lottery = LotteryManager(self.users)
        total = len(prizes)
        print("\n========== Lottery Started ==========")
        for round_number, prize in enumerate(prizes, start=1):
            self._run_round(prize, round_number, total)

        print("\n========== Lottery Completed ==========")
        self._show_winners()
        if self._confirm("Export winners now"):
            self._export()

    def _run_round(self, prize: Prize, round_number: int, total: int) -> None:
        assert self.lottery is not None
        print(f"\n--- Round {round_number}/{total}: {prize.name} | Quantity: {prize.quantity} ---")
        print(f"Rule: {prize.rule_description()}")
        if prize.associated_drawer == MA_JIAQI and self.lottery.is_fallback_active():
            print("Protection rule active: only Cheng Ru Group members are eligible.")

        self.lottery.start_round(prize)
        drawn = 0
        terminated = False
        while drawn < prize.quantity:
            print(f"Currently drawing the {ordinal(drawn + 1)} winner")
            command = self._ask(
                "Press Enter to draw, or type 'pause' / 'terminate': "
            ).lower()
            if command == "terminate":
                terminated = True
                break
            if command == "pause":
                if not self._pause_loop():
                    terminated = True
                    break
            elif command:
                print("Unknown command.")
                continue

            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize; round ends early.")
                break
            self.result_manager.add_winner(user, prize)
            drawn += 1
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        self.lottery.end_round()
        if terminated:
            print("Round terminated by operator.")

        winners = self.result_manager.get_winners_by_prize([prize]).get(prize.name, [])
        print(f"\nRound results for {prize.name}:")
        if not winners:
            print("  (no winners)")
        for winner in winners:
            print(
                f"  #{winner.winning_order} {winner.user.name} "
                f"({winner.user.department})"
            )

    def _pause_loop(self) -> bool:
        """Pause until 'continue' (returns True) or 'terminate' (returns False)."""
        print("Lottery paused.")
        while True:
            command = self._ask("Type 'continue' to resume or 'terminate' to end this round: ").lower()
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Unknown command. Please type 'continue' or 'terminate'.")

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #
    def _show_winners(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        grouped = self.result_manager.get_winners_by_prize(prizes)
        total = 0
        print("\n========== Winner List ==========")
        for prize in prizes:
            print(f"{prize.name}:")
            winners = grouped.get(prize.name, [])
            if not winners:
                print("  (no winners)")
            for winner in winners:
                total += 1
                print(
                    f"  {winner.user.name} | {winner.user.department} | {prize.name}"
                )
        print(f"Total winners: {total}")

    def _export(self) -> None:
        if not self.result_manager.winners:
            print("No winners to export yet.")
            return
        _, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    LotteryCLI().run()


if __name__ == "__main__":
    main()
