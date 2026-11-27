"""Command-line interaction for the team building lottery."""
from __future__ import annotations

from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager, Winner
from lottery_system.models import LOTTERY_PERSONS, Prize

SEPARATOR = "=" * 64


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryCLI:
    """Interactive console application controlling the whole lottery process."""

    def __init__(self):
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users = []
        self.groups: dict[str, int] = {}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ask(prompt: str) -> str:
        return input(prompt).strip()

    # ---------------------------------------------------------------- main flow
    def run(self) -> None:
        print(SEPARATOR)
        print("Company Team Building Event - Smart Lottery System")
        print(SEPARATOR)
        users = self._setup_participants()
        if users is None:
            print("Goodbye!")
            return
        self._setup_prizes()
        print("Goodbye!")

    # ------------------------------------------------------ participant list
    def _setup_participants(self):
        while True:
            print("\n--- Participant List ---")
            print("1. Load built-in default list")
            print("2. Upload custom txt list (format: Name,Department Group per line)")
            print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "0":
                return None
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
                source = "built-in default list"
            elif choice == "2":
                path = self._ask("Enter the txt file path: ")
                users, errors = self.list_manager.load_custom_list(path)
                source = path
            else:
                print("Invalid option.")
                continue

            valid, duplicates = self.list_manager.validate_users(users)
            if errors or duplicates:
                print("\nIssues found in the list:")
                for error in errors:
                    print(f"  - {error}")
                for dup in duplicates:
                    print(f"  - Duplicate Name: '{dup.name}' ({dup.department}) appears more "
                          "than once; the first occurrence is kept.")
                print("Enter 'r' to remove invalid data and continue, "
                      "or 't' to terminate this upload.")
                action = self._ask("Your choice (r/t): ").lower()
                if action == "t":
                    print("Upload terminated.")
                    continue
                if action != "r":
                    print("Invalid choice. Upload terminated.")
                    continue

            if not valid:
                print("No valid participants found. Please try again.")
                continue

            self.users = valid
            self.groups = self.list_manager.get_group_info(valid)
            print(f"\nLoaded {len(valid)} participants from {source}.")
            print("Department groups:")
            for group, count in self.groups.items():
                print(f"  - {group}: {count} people")
            return valid

    # ----------------------------------------------------------- prize config
    def _setup_prizes(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prize library")
            print("2. Add custom prize")
            print("3. Set avoidance groups for a prize")
            print("4. Reorder lottery sequence")
            print("5. View prizes")
            print("6. Start lottery")
            print("0. Exit")
            choice = self._ask("Select an option: ")
            if choice == "1":
                errors = self.prize_manager.load_default_prizes()
                if errors:
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print("Preset prizes loaded.")
            elif choice == "2":
                self._add_custom_prize()
            elif choice == "3":
                self._configure_avoid_groups()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._show_prizes()
            elif choice == "6":
                if not self.prize_manager.get_prizes():
                    print("Please add at least one prize first.")
                    continue
                self._run_lottery()
                return
            elif choice == "0":
                return
            else:
                print("Invalid option.")

    def _parse_group_selection(self, text: str) -> list[str] | None:
        """Accept group numbers (from the group list) or exact group names, comma separated."""
        group_names = list(self.groups.keys())
        selected: list[str] = []
        if not text.strip():
            return []
        for token in [t.strip() for t in text.split(",") if t.strip()]:
            if token.isdigit():
                index = int(token)
                if not 1 <= index <= len(group_names):
                    return None
                name = group_names[index - 1]
            elif token in group_names:
                name = token
            else:
                return None
            if name not in selected:
                selected.append(name)
        return selected

    def _show_group_choices(self) -> None:
        print("Available department groups:")
        for idx, (group, count) in enumerate(self.groups.items(), start=1):
            print(f"  {idx}. {group} ({count} people)")

    def _add_custom_prize(self) -> None:
        name = self._ask("Prize name: ")
        try:
            quantity = int(self._ask("Quantity: "))
        except ValueError:
            print("Quantity must be an integer.")
            return
        self._show_group_choices()
        groups_text = self._ask("Avoidance groups (numbers or names, comma separated; empty for none): ")
        groups = self._parse_group_selection(groups_text)
        if groups is None:
            print("Invalid group selection. Prize not added.")
            return
        print("Associated lottery person (optional):")
        print("  0. None")
        for idx, person in enumerate(LOTTERY_PERSONS, start=1):
            print(f"  {idx}. {person}")
        drawer_text = self._ask("Select (0-4): ")
        drawer = None
        if drawer_text.isdigit() and 1 <= int(drawer_text) <= len(LOTTERY_PERSONS):
            drawer = LOTTERY_PERSONS[int(drawer_text) - 1]
        elif drawer_text not in ("", "0"):
            print("Invalid selection. Prize not added.")
            return
        try:
            prize = self.prize_manager.add_prize(name, quantity, groups, drawer)
            print(f"Prize added: {prize.name} (quantity {prize.quantity}).")
        except ValueError as exc:
            print(f"Prize not added: {exc}")

    def _configure_avoid_groups(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        try:
            index = int(self._ask("Select prize number: "))
            prize = prizes[index - 1]
        except (ValueError, IndexError):
            print("Invalid prize number.")
            return
        self._show_group_choices()
        groups_text = self._ask("Avoidance groups (numbers or names, comma separated; empty to clear): ")
        groups = self._parse_group_selection(groups_text)
        if groups is None:
            print("Invalid group selection.")
            return
        self.prize_manager.set_avoid_groups(prize.name, groups)
        print(f"Avoidance groups for '{prize.name}': {', '.join(groups) if groups else 'none'}")

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        self._show_prizes()
        text = self._ask("Enter new order as serial numbers (e.g. 3 1 2): ")
        try:
            order = [int(x) for x in text.replace(",", " ").split()]
        except ValueError:
            print("Invalid input.")
            return
        if self.prize_manager.reorder_prizes(order):
            print("Lottery sequence updated.")
            self._show_prizes()
        else:
            print("Invalid order: every prize number must appear exactly once.")

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Lottery sequence:")
        for idx, prize in enumerate(prizes, start=1):
            groups = ", ".join(prize.avoid_groups) if prize.avoid_groups else "none"
            drawer = prize.associated_drawer or "none"
            print(f"  {idx}. {prize.name} | quantity: {prize.quantity} | "
                  f"avoid groups: {groups} | drawer: {drawer}")

    # -------------------------------------------------------- lottery process
    def _await_command(self) -> str:
        """Wait for user input before a draw. Returns 'draw' or 'skip'."""
        while True:
            cmd = self._ask("Press Enter to draw (commands: pause / terminate): ").lower()
            if cmd in ("", "continue"):
                return "draw"
            if cmd == "terminate":
                return "skip"
            if cmd == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    sub = self._ask("> ").lower()
                    if sub == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if sub == "terminate":
                        return "skip"
                    print("Unknown command. Use 'continue' or 'terminate'.")
            print("Unknown command. Use Enter, 'pause', or 'terminate'.")

    def _run_lottery(self) -> None:
        lottery = LotteryManager(self.users)
        prizes = self.prize_manager.get_prizes()

        for round_no, prize in enumerate(prizes, start=1):
            print("\n" + SEPARATOR)
            print(f"Round {round_no}: {prize.name} | Quantity: {prize.quantity}")
            print(f"Rule: {lottery.get_rule_description(prize)}")
            print(SEPARATOR)

            round_winners: list[Winner] = []
            drawn = 0
            while drawn < prize.quantity:
                if lottery.get_eligible_count(prize) == 0:
                    print("No eligible participants remain for this prize. Round ends.")
                    break
                action = self._await_command()
                if action == "skip":
                    remaining = prize.quantity - drawn
                    print(f"Round terminated. Skipping {remaining} remaining winner(s).")
                    break
                print(f"Currently drawing the {ordinal(drawn + 1)} winner...")
                user = lottery.draw_winner(prize)
                if user is None:
                    print("No eligible participants remain for this prize. Round ends.")
                    break
                winner = self.result_manager.add_winner(user, prize)
                round_winners.append(winner)
                drawn += 1
                print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}!")

            lottery.end_round(prize)

            print(f"\nRound {round_no} results:")
            if not round_winners:
                print("  No winners in this round.")
            for w in round_winners:
                print(f"  #{w.winning_order} {w.user.name} ({w.user.department}) - {w.prize_name}")

        self._show_summary(prizes)
        self._export_prompt(prizes)

    def _show_summary(self, prizes: list[Prize]) -> None:
        print("\n" + SEPARATOR)
        print("Final Winner List (by prize level, high to low)")
        print(SEPARATOR)
        grouped = self.result_manager.get_winners_by_prize(prizes)
        for prize_name, winners in grouped.items():
            print(f"\n{prize_name}:")
            if not winners:
                print("  (no winners)")
            for w in winners:
                print(f"  {w.user.name} ({w.user.department}) - {w.winning_time:%Y-%m-%d %H:%M:%S}")

    def _export_prompt(self, prizes: list[Prize]) -> None:
        answer = self._ask("\nExport the winner list to a txt (CSV format) file? (y/n): ").lower()
        if answer in ("y", "yes"):
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)
        else:
            print("Export skipped.")


def main() -> int:
    try:
        LotteryCLI().run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
    return 0
