"""Command-line interaction for the lottery process."""

from lottery_system.constants import KNOWN_DRAWERS
from lottery_system.models import Prize, User, normalize_text
from lottery_system.services.list_manager import ListManager
from lottery_system.services.lottery_manager import LotteryManager
from lottery_system.services.prize_manager import PrizeManager
from lottery_system.services.result_manager import ResultManager


class ExitRequested(Exception):
    """Raised when standard input is closed."""


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise ExitRequested()


def ask_yes(prompt: str) -> bool:
    return ask(prompt).lower() in ("y", "yes")


def ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class LotteryApp:
    """Drives the full interactive lottery workflow."""

    def __init__(self) -> None:
        self.list_manager = ListManager()
        self.prize_manager = PrizeManager()
        self.result_manager = ResultManager()
        self.users: list[User] = []
        self.lottery: LotteryManager | None = None

    # ---------- top level ----------

    def run(self) -> int:
        self._banner()
        try:
            if not self._load_participants():
                print("No participant list loaded. Exiting.")
                return 0
            self._configure_prizes()
            self._run_lottery()
        except ExitRequested:
            print("\nInput closed. Exiting.")
            return 0
        print("Thank you for using the lottery system.")
        return 0

    def _banner(self) -> None:
        print("=" * 60)
        print("  Company Team Building Event - Smart Lottery System")
        print("=" * 60)

    # ---------- 2.1 list management ----------

    def _load_participants(self) -> bool:
        while True:
            print("\n--- Participant List ---")
            print("1. Load built-in default team building list")
            print("2. Upload custom txt list (format: Name,Department Group per line)")
            print("0. Exit")
            choice = ask("Select an option: ")
            if choice == "1":
                users, errors = self.list_manager.load_default_list()
                if self._accept_users(users, errors):
                    return True
            elif choice == "2":
                path = ask("Enter the path of the txt file: ")
                users, errors = self.list_manager.load_custom_list(path)
                if self._accept_users(users, errors):
                    return True
            elif choice == "0":
                return False
            else:
                print("Invalid option.")

    def _accept_users(self, users: list[User], errors: list[str]) -> bool:
        if errors:
            print(f"Validation found {len(errors)} problem(s):")
            for error in errors:
                print(f"  - {error}")
            print("Choose 'y' to remove the invalid data and continue with valid entries,")
            print("or 'n' to terminate this upload.")
            if not ask_yes("Remove invalid data and continue? [y/N]: "):
                print("Upload terminated.")
                return False
        if not users:
            print("No valid participants found.")
            return False
        self.users = users
        print(f"Loaded {len(users)} participant(s).")
        self._print_groups()
        return True

    def _print_groups(self) -> None:
        groups = self.list_manager.get_group_info(self.users)
        print("Department groups:")
        for group, count in groups.items():
            print(f"  {group}: {count} member(s)")

    # ---------- 2.2 prize configuration ----------

    def _configure_prizes(self) -> None:
        while True:
            print("\n--- Prize Configuration ---")
            print("1. Load preset prizes")
            print("2. Add custom prize")
            print("3. View prize list")
            print("4. Reorder prizes")
            print("5. View participant groups")
            print("0. Finish configuration and continue")
            choice = ask("Select an option: ")
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
                self._show_prizes()
            elif choice == "4":
                self._reorder_prizes()
            elif choice == "5":
                self._print_groups()
            elif choice == "0":
                if not self.prize_manager.get_prizes():
                    print("Add at least one prize before starting the lottery.")
                    continue
                return
            else:
                print("Invalid option.")

    def _parse_groups(self, text: str) -> list[str]:
        groups = self.list_manager.get_group_info(self.users)
        names = list(groups.keys())
        selected: list[str] = []
        tokens = [token.strip() for token in text.split(",") if token.strip()]
        for token in tokens:
            if token.isdigit() and 1 <= int(token) <= len(names):
                name = names[int(token) - 1]
            else:
                matches = [n for n in names if normalize_text(n) == normalize_text(token)]
                if not matches:
                    raise ValueError(f"Unknown group: '{token}'")
                name = matches[0]
            if name not in selected:
                selected.append(name)
        return selected

    def _add_custom_prize(self) -> None:
        name = ask("Prize name: ")
        if not name:
            print("Prize name cannot be empty.")
            return
        quantity_text = ask("Quantity: ")
        if not quantity_text.isdigit() or int(quantity_text) <= 0:
            print("Quantity must be a positive integer.")
            return

        groups = self.list_manager.get_group_info(self.users)
        print("Available department groups:")
        for index, (group, count) in enumerate(groups.items(), start=1):
            print(f"  {index}. {group} ({count})")
        groups_text = ask("Avoidance groups (numbers or names, comma-separated; blank for none): ")
        try:
            avoid_groups = self._parse_groups(groups_text)
        except ValueError as exc:
            print(exc)
            return

        print("Known lottery persons: " + ", ".join(KNOWN_DRAWERS))
        drawer = ask("Associated lottery person (blank for none): ")
        try:
            prize = self.prize_manager.add_prize(
                name, int(quantity_text), avoid_groups, drawer or None
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        print(f"Prize added: {prize.name} (quantity {prize.quantity})")

    def _describe_prize_line(self, index: int, prize: Prize) -> str:
        avoid = ", ".join(prize.avoid_groups) if prize.avoid_groups else "None"
        drawer = prize.associated_drawer or "None"
        return (
            f"{index}. {prize.name} | Quantity: {prize.quantity} | "
            f"Avoid: {avoid} | Lottery person: {drawer}"
        )

    def _show_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes configured.")
            return
        print("Prize sequence:")
        for index, prize in enumerate(prizes, start=1):
            print("  " + self._describe_prize_line(index, prize))

    def _reorder_prizes(self) -> None:
        prizes = self.prize_manager.get_prizes()
        if not prizes:
            print("No prizes to reorder.")
            return
        self._show_prizes()
        text = ask("Enter the new order as serial numbers (e.g., 2 1 3): ")
        tokens = text.replace(",", " ").split()
        if not tokens or not all(token.isdigit() for token in tokens):
            print("Invalid input: please enter serial numbers only.")
            return
        order = [int(token) for token in tokens]
        if self.prize_manager.reorder_prizes(order):
            print("Prize order updated.")
        else:
            print("Invalid order: every serial number must appear exactly once.")

    # ---------- 2.3 / 2.4 / 2.5 lottery process ----------

    def _run_lottery(self) -> None:
        prizes = self.prize_manager.get_prizes()
        print("\n=== Lottery Overview ===")
        for index, prize in enumerate(prizes, start=1):
            print(self._describe_prize_line(index, prize))

        if not ask_yes("Start the lottery now? [y/N]: "):
            print("Lottery not started.")
            return

        self.lottery = LotteryManager(self.users)
        print(
            "Controls: press Enter to draw the next winner | 'pause' to pause | "
            "'terminate' to end the current round | 'continue' to resume."
        )
        for index, prize in enumerate(prizes, start=1):
            self._run_round(index, len(prizes), prize)

        self._show_final_results(prizes)
        if ask_yes("Export the winner list to a CSV-formatted txt file? [y/N]: "):
            _, message = self.result_manager.export_to_csv(prizes)
            print(message)

    def _run_round(self, index: int, total: int, prize: Prize) -> None:
        assert self.lottery is not None
        print(f"\n=== Round {index}/{total}: {prize.name} | Quantity: {prize.quantity} ===")
        print(f"Rule: {self.lottery.describe_rule(prize)}")

        round_winners: list[User] = []
        for position in range(1, prize.quantity + 1):
            if self._wait_for_next_draw() == "terminate":
                print("Round terminated manually; remaining draws skipped.")
                break
            print(f"Currently drawing the {ordinal(position)} winner...")
            user = self.lottery.draw_one(prize)
            if user is None:
                print("No eligible candidates remain for this prize; round ends early.")
                break
            self.result_manager.add_winner(user, prize)
            round_winners.append(user)
            print(f"Congratulations {user.name} ({user.department}) for winning {prize.name}")

        print(f"--- Round {index} results (winning order) ---")
        if round_winners:
            for order, user in enumerate(round_winners, start=1):
                print(f"  {order}. {user.name} ({user.department})")
        else:
            print("  No winners in this round.")

    def _wait_for_next_draw(self) -> str:
        """Gate before each draw. Returns 'draw' or 'terminate'."""
        while True:
            command = ask("[Enter] draw next | pause | terminate > ").lower()
            if command in ("", "draw", "continue"):
                return "draw"
            if command == "terminate":
                return "terminate"
            if command == "pause":
                print("Lottery paused. Type 'continue' to resume or 'terminate' to end this round.")
                while True:
                    sub_command = ask("(paused) > ").lower()
                    if sub_command == "continue":
                        print("Lottery resumed.")
                        return "draw"
                    if sub_command == "terminate":
                        return "terminate"
                    print("Type 'continue' to resume or 'terminate' to end this round.")
            print("Unknown command. Use Enter, 'pause', or 'terminate'.")

    def _show_final_results(self, prizes: list[Prize]) -> None:
        print("\n=== Final Winner List ===")
        grouped = self.result_manager.get_winners_by_prize(prizes)
        total = 0
        for prize in prizes:
            winners = grouped.get(prize.name, [])
            print(f"{prize.name} ({len(winners)}/{prize.quantity})")
            if not winners:
                print("  (no winners)")
            for winner in winners:
                total += 1
                print(
                    f"  {winner.draw_order}. {winner.user.name} | "
                    f"{winner.user.department} | {winner.prize_name}"
                )
        print(f"Total winners: {total}")


def main(argv: list[str] | None = None) -> int:
    app = LotteryApp()
    try:
        return app.run()
    except KeyboardInterrupt:
        print("\nLottery interrupted.")
        return 130
