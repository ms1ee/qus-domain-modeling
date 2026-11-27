"""Command-line interface for the company team building lottery system."""

from __future__ import annotations

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI, Prize, User, normalize
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager

SUGGESTED_DRAWERS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]


def ordinal(number: int) -> str:
    """Format an integer as an English ordinal (1st, 2nd, 11th...)."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


class LotteryCLI:
    """Interactive command-line controller."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None
        self.lottery_completed = False

    # ------------------------------------------------------------------ main
    def run(self) -> None:
        self._print_banner()
        while True:
            self._print_status()
            print("\nMain Menu")
            print("  1. Load participant list")
            print("  2. View department groups")
            print("  3. Configure prizes")
            print("  4. Start lottery")
            print("  5. View results")
            print("  6. Export results to file")
            print("  0. Exit")
            choice = input("Select an option: ").strip()
            if choice == "1":
                self.load_participants()
            elif choice == "2":
                self._show_groups()
            elif choice == "3":
                self.configure_prizes()
            elif choice == "4":
                self.start_lottery()
            elif choice == "5":
                self.show_results()
            elif choice == "6":
                self.export_results()
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid option, please try again.")

    @staticmethod
    def _print_banner() -> None:
        print("=" * 60)
        print("  Company Team Building Smart Lottery System")
        print("=" * 60)

    def _print_status(self) -> None:
        print(
            f"\n[Status] Participants: {len(self.users)} | "
            f"Prizes: {len(self.prize_manager.get_prizes())} | "
            f"Lottery completed: {'yes' if self.lottery_completed else 'no'}"
        )

    # ------------------------------------------------------- participants
    def load_participants(self) -> None:
        print("\nParticipant list source:")
        print("  1. Built-in default team building list")
        print("  2. Custom txt file (each line: Name,Department Group)")
        print("  0. Back")
        choice = input("Select an option: ").strip()
        if choice == "1":
            users, errors = self.list_manager.load_default_list()
        elif choice == "2":
            path = input("Enter the txt file path: ").strip().strip('"').strip("'")
            if not path:
                print("No path entered.")
                return
            users, errors = self.list_manager.load_custom_list(path)
        else:
            return
        self._apply_import(users, errors)

    def _apply_import(self, users: list[User], errors: list[str]) -> None:
        if errors:
            print(f"\n{len(errors)} format error(s) found:")
            for error in errors:
                print("  - " + error)
        valid, duplicates = self.list_manager.validate_users(users)
        if duplicates:
            print(f"\n{len(duplicates)} duplicate name(s) found:")
            for user in duplicates:
                print(f"  - {user.name} ({user.department})")
        if errors or duplicates:
            print("\nType 'r' to remove invalid and duplicate entries and continue,")
            print("or 'q' to terminate the upload.")
            choice = normalize(input("Your choice: "))
            if choice != "r":
                print("Upload terminated. The previous participant list is unchanged.")
                return
        if not valid:
            print("No valid participants found. Upload aborted.")
            return
        self.users = valid
        self.lottery_completed = False
        print(f"Loaded {len(valid)} participant(s).")
        self._show_groups()

    def _show_groups(self) -> None:
        if not self.users:
            print("No participants loaded.")
            return
        groups = self.list_manager.get_group_info(self.users)
        print("\nDepartment groups:")
        for index, (group, count) in enumerate(groups.items(), start=1):
            print(f"  {index}. {group}: {count} person(s)")
        print(f"Total: {len(self.users)} participant(s) in {len(groups)} group(s).")

    # ------------------------------------------------------------- prizes
    def configure_prizes(self) -> None:
        while True:
            print("\nPrize Configuration")
            print("  1. Load default prize library")
            print("  2. Add custom prize")
            print("  3. Set avoidance groups for a prize")
            print("  4. Set associated lottery person for a prize")
            print("  5. View prizes")
            print("  6. Reorder lottery sequence")
            print("  0. Back")
            choice = input("Select an option: ").strip()
            if choice == "1":
                self._load_prize_library()
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._set_prize_groups()
            elif choice == "4":
                self._set_prize_drawer()
            elif choice == "5":
                self._view_prizes()
            elif choice == "6":
                self._reorder_prizes()
            elif choice == "0":
                return
            else:
                print("Invalid option, please try again.")

    def _load_prize_library(self) -> None:
        errors = self.prize_manager.load_default_prizes()
        if errors:
            for error in errors:
                print(error)
        else:
            print("Default prize library loaded.")

    def _add_custom_prize(self) -> None:
        name = input("Prize name: ").strip()
        quantity_text = input("Quantity: ").strip()
        if not quantity_text.isdigit() or int(quantity_text) < 1:
            print("Quantity must be a positive whole number.")
            return
        groups = self._select_groups()
        drawer = self._select_drawer()
        try:
            self.prize_manager.add_prize(name, int(quantity_text), groups, drawer)
        except ValueError as exc:
            print(f"Cannot add prize: {exc}")
            return
        print(f"Prize '{' '.join(name.split())}' added.")

    def _select_groups(self) -> list[str]:
        groups = list(self.list_manager.get_group_info(self.users).keys()) if self.users else []
        if groups:
            print("Available department groups:")
            for index, group in enumerate(groups, start=1):
                print(f"  {index}. {group}")
        else:
            print("(No participant list loaded; group names can be typed directly.)")
        raw = input("Avoidance groups (numbers or names, comma separated, blank for none): ")
        selected: list[str] = []
        seen: set[str] = set()
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if token.isdigit() and groups:
                index = int(token)
                if not 1 <= index <= len(groups):
                    print(f"Invalid group number: {token}")
                    continue
                name = groups[index - 1]
            else:
                name = next((g for g in groups if normalize(g) == normalize(token)), token)
                if groups and name not in groups:
                    print(f"Warning: group '{token}' is not in the loaded participant list.")
            key = normalize(name)
            if key not in seen:
                seen.add(key)
                selected.append(name)
        return selected

    @staticmethod
    def _select_drawer() -> str | None:
        print("Suggested lottery persons: " + ", ".join(SUGGESTED_DRAWERS))
        raw = input("Associated lottery person (blank for none): ").strip()
        return raw or None

    def _select_prize_index(self) -> int | None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return None
        self._view_prizes()
        raw = input("Select prize number: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(prizes):
            print("Invalid prize number.")
            return None
        return int(raw) - 1

    def _set_prize_groups(self) -> None:
        index = self._select_prize_index()
        if index is None:
            return
        prize = self.prize_manager.get_prizes()[index]
        prize.avoid_groups = self._select_groups()
        print(f"Avoidance groups for '{prize.name}': {', '.join(prize.avoid_groups) or 'None'}")

    def _set_prize_drawer(self) -> None:
        index = self._select_prize_index()
        if index is None:
            return
        prize = self.prize_manager.get_prizes()[index]
        prize.associated_drawer = self._select_drawer()
        print(f"Associated lottery person for '{prize.name}': {prize.associated_drawer or 'None'}")

    def _view_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        print("\nPrizes (lottery order):")
        for index, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) or "None"
            drawer = prize.associated_drawer or "None"
            print(
                f"  {index}. {prize.name} | Quantity: {prize.quantity} | "
                f"Avoid groups: {groups} | Lottery person: {drawer}"
            )

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured yet.")
            return
        self._view_prizes()
        raw = input("Enter the new order as serial numbers (e.g. 2 1 3): ")
        tokens = raw.replace(",", " ").split()
        try:
            order = [int(token) for token in tokens]
        except ValueError:
            print("Invalid input: please enter serial numbers only.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
        else:
            print("Invalid order: each prize number must appear exactly once.")

    # ------------------------------------------------------------ lottery
    def start_lottery(self) -> None:
        if self.lottery_completed:
            print("The lottery has already been completed in this session.")
            return
        if not self.users:
            print("Please load a participant list first.")
            return
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("Please configure at least one prize first.")
            return
        total = sum(prize.quantity for prize in prizes)
        if total > len(self.users):
            print(
                f"Warning: total prize quantity ({total}) exceeds participants "
                f"({len(self.users)}); some rounds may end early."
            )
            if normalize(input("Continue? (y/n): ")) not in ("y", "yes"):
                return

        self.lottery = LotteryManager(self.users)
        print("\nLottery starting! Commands: Enter = draw, 'pause', 'terminate'.")
        for round_no, prize in enumerate(prizes, start=1):
            self._run_round(round_no, len(prizes), prize)
        self.lottery_completed = True
        print("\nAll lottery rounds completed.")
        self.show_results()

    def _run_round(self, round_no: int, total_rounds: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n----- Round {round_no}/{total_rounds}: {prize.name} -----")
        print(f"Quantity: {prize.quantity}")
        print(f"Rules: {self.lottery.describe_rules(prize)}")
        self.lottery.begin_round(prize)

        drawn = 0
        terminated = False
        while drawn < prize.quantity:
            if not self.lottery.has_candidates(prize):
                print("No eligible candidates remain for this prize.")
                break
            command = normalize(
                input("Press Enter to draw the next winner (or 'pause' / 'terminate'): ")
            )
            if command == "terminate":
                print("Terminating the current round.")
                terminated = True
                break
            if command == "pause":
                if not self._handle_pause():
                    print("Terminating the current round.")
                    terminated = True
                    break
                continue
            if command:
                print("Unknown command. Press Enter to draw, or type 'pause' / 'terminate'.")
                continue

            print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
            user = self.lottery.draw_next(prize)
            if user is None:
                print("No eligible candidates remain for this prize.")
                break
            drawn += 1
            self.result_manager.add_winner(user, prize)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

        winners = self.lottery.end_round(prize)
        print(f"\nRound finished: {len(winners)} of {prize.quantity} winner(s) drawn.")
        if terminated:
            print("(Round ended early by terminate command.)")
        if winners:
            print("Round results (winning order):")
            for index, user in enumerate(winners, start=1):
                print(f"  {index}. {user.name} ({user.department})")

    @staticmethod
    def _handle_pause() -> bool:
        """Pause the lottery. Returns True to resume, False to terminate the round."""
        print("Lottery paused.")
        while True:
            command = normalize(
                input("Type 'continue' to resume or 'terminate' to end this round: ")
            )
            if command == "continue":
                print("Lottery resumed.")
                return True
            if command == "terminate":
                return False
            print("Unknown command.")

    # ------------------------------------------------------------ results
    def show_results(self) -> None:
        winners = self.result_manager.get_winners()
        if not winners:
            print("No winners recorded yet.")
            return
        prizes = self.prize_manager.get_prizes()
        grouped = self.result_manager.get_winners_by_prize(prizes)
        print("\n===== Winner List (prize level from high to low) =====")
        for prize_name, items in grouped.items():
            if not items:
                continue
            print(f"\n[{prize_name}]")
            for winner in items:
                print(f"  #{winner.sequence}  {winner.user.name} ({winner.user.department})")

    def export_results(self) -> None:
        if not self.result_manager.get_winners():
            print("No winners recorded yet; nothing to export.")
            return
        success, message = self.result_manager.export_to_csv(self.prize_manager.get_prizes())
        print(message)


def main() -> None:
    """Entry point for the lottery command-line program."""
    try:
        LotteryCLI().run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting the lottery system.")
